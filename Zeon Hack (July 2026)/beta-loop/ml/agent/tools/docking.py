"""GNINA batch docking helpers for reverse selection (Phase B R2)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agent.paths import COMPOUND_DOSSIERS_JSON, DOCKING_RECEPTOR_DIR, LOCAL_DOCKING, REPO_ROOT
from agent.tools.chem import RDKIT_AVAILABLE

DEFAULT_TEM1_PDB = "1JQL"

# Common crystallographic ions/solvents — not useful for autobox definition.
_AUTobox_EXCLUDE_RESNAMES = frozenset(
    {
        "HOH",
        "WAT",
        "PO4",
        "CL",
        "NA",
        "K",
        "MG",
        "CA",
        "ZN",
        "FE",
        "MN",
        "CU",
        "NI",
        "CO",
        "CD",
        "IOD",
        "BR",
        "F",
        "NO3",
        "ACT",
        "DMS",
        "EDO",
        "GOL",
        "PEG",
        "BME",
    }
)

_CNN_AFFINITY_RE = re.compile(r"CNNaffinity\s+(-?\d+(?:\.\d+)?)", re.I)

# RCSB 1JQL is DNA polymerase; project docs use the code as a TEM-1 alias.
TEM1_STRUCTURE_PDB = "1XPB"


def resolve_receptor_pdb(pdb_id: str) -> tuple[str, str | None]:
    """Map project receptor codes to an RCSB structure suitable for TEM-1 docking."""
    requested = pdb_id.upper()
    if requested == "1JQL":
        return TEM1_STRUCTURE_PDB, (
            "Alias 1JQL → 1XPB (TEM-1 β-lactamase). RCSB 1JQL is unrelated (DNA polymerase)."
        )
    return requested, None


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gnina_status() -> dict[str, Any]:
    """Return whether the GNINA CLI is available on PATH or via GNINA_BIN."""
    binary = resolve_gnina_binary()
    return {
        "available": binary is not None,
        "binary": binary,
        "rdkit": RDKIT_AVAILABLE,
    }


def resolve_gnina_binary() -> str | None:
    override = os.environ.get("GNINA_BIN", "").strip()
    if override:
        path = Path(override)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    found = shutil.which("gnina")
    return found


def fetch_pdb(pdb_id: str, dest: Path) -> Path:
    """Download a PDB file from RCSB if not already cached."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            dest.write_bytes(response.read())
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download {pdb_id} from RCSB: {exc}") from exc
    return dest


def _het_key(line: str) -> tuple[str, str, str] | None:
    if not line.startswith("HETATM"):
        return None
    return (line[21:22].strip(), line[22:26].strip(), line[17:20].strip())


def prepare_receptor(pdb_id: str = DEFAULT_TEM1_PDB, work_dir: Path | None = None) -> dict[str, Any]:
    """Download PDB and split protein (receptor) from co-crystal ligand for autobox."""
    cache_dir = work_dir or DOCKING_RECEPTOR_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)
    requested_pdb = pdb_id.upper()
    effective_pdb, alias_note = resolve_receptor_pdb(requested_pdb)
    raw_pdb = fetch_pdb(effective_pdb, cache_dir / f"{effective_pdb}.pdb")

    receptor_lines: list[str] = []
    het_groups: dict[tuple[str, str, str], list[str]] = {}

    for line in raw_pdb.read_text().splitlines():
        if line.startswith("ATOM"):
            receptor_lines.append(line)
        elif line.startswith("HETATM"):
            key = _het_key(line)
            if key is None:
                continue
            _, _, resname = key
            if resname in _AUTobox_EXCLUDE_RESNAMES:
                continue
            het_groups.setdefault(key, []).append(line)

    if not het_groups:
        raise RuntimeError(
            f"No autobox ligand found in {effective_pdb}.pdb "
            f"(requested {requested_pdb}). Try TEM1_STRUCTURE_PDB={TEM1_STRUCTURE_PDB}."
        )

    ion_resnames = {"SO4", "PO4", "NO3"}
    non_ion = {k: v for k, v in het_groups.items() if k[2] not in ion_resnames}
    autobox_key = max(non_ion or het_groups, key=lambda k: len((non_ion or het_groups)[k]))
    autobox_resname = autobox_key[2]

    receptor_path = cache_dir / f"{effective_pdb}_receptor.pdb"
    autobox_path = cache_dir / f"{effective_pdb}_autobox.pdb"
    receptor_path.write_text("\n".join(receptor_lines) + "\nEND\n")
    autobox_path.write_text("\n".join(het_groups[autobox_key]) + "\nEND\n")

    return {
        "requested_pdb": requested_pdb,
        "effective_pdb": effective_pdb,
        "alias_note": alias_note,
        "raw_pdb": raw_pdb,
        "receptor_pdb": receptor_path,
        "autobox_ligand_pdb": autobox_path,
        "autobox_residue": autobox_resname,
    }


def smiles_to_sdf(smiles: str, out_path: Path) -> bool:
    """Embed SMILES to 3D and write an SDF for GNINA."""
    if not RDKIT_AVAILABLE or not smiles:
        return False
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    mol = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mol, randomSeed=0xC0FFEE) != 0:
        return False
    try:
        AllChem.UFFOptimizeMolecule(mol, maxIters=200)
    except Exception:
        pass
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(out_path))
    writer.write(mol)
    writer.close()
    return out_path.exists() and out_path.stat().st_size > 0


def parse_gnina_cnn_affinity(sdf_path: Path, log_path: Path | None = None) -> float | None:
    """Parse CNN affinity from GNINA output SDF (best pose) or log file."""
    if RDKIT_AVAILABLE and sdf_path.exists():
        from rdkit import Chem

        supplier = Chem.SDMolSupplier(str(sdf_path), removeHs=False)
        best: float | None = None
        for mol in supplier:
            if mol is None:
                continue
            if mol.HasProp("CNNaffinity"):
                value = float(mol.GetProp("CNNaffinity"))
            elif mol.HasProp("minimizedAffinity"):
                value = float(mol.GetProp("minimizedAffinity"))
            else:
                continue
            if best is None or value < best:
                best = value
        if best is not None:
            return best

    if log_path and log_path.exists():
        match = _CNN_AFFINITY_RE.search(log_path.read_text())
        if match:
            return float(match.group(1))
    return None


def run_gnina_dock(
    *,
    gnina_bin: str,
    receptor_pdb: Path,
    autobox_ligand_pdb: Path,
    ligand_sdf: Path,
    out_dir: Path,
    exhaustiveness: int = 8,
    timeout_sec: int = 600,
) -> dict[str, Any]:
    """Dock one ligand with GNINA; write pose SDF and log under out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_sdf = out_dir / "docked.sdf"
    log_path = out_dir / "gnina.log"

    cmd = [
        gnina_bin,
        "-r",
        str(receptor_pdb),
        "-l",
        str(ligand_sdf),
        "--autobox_ligand",
        str(autobox_ligand_pdb),
        "-o",
        str(out_sdf),
        "--log",
        str(log_path),
        "--exhaustiveness",
        str(exhaustiveness),
    ]

    started = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "command": cmd,
            "elapsed_sec": timeout_sec,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    combined_log = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if proc.returncode != 0:
        if log_path.exists():
            combined_log = log_path.read_text() + "\n" + combined_log
        return {
            "status": "error",
            "returncode": proc.returncode,
            "command": cmd,
            "elapsed_sec": elapsed,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "log_path": str(log_path),
        }

    affinity = parse_gnina_cnn_affinity(out_sdf, log_path)
    if affinity is None and combined_log:
        match = _CNN_AFFINITY_RE.search(combined_log)
        if match:
            affinity = float(match.group(1))

    return {
        "status": "ok" if affinity is not None else "no_score",
        "gnina_cnn_affinity": affinity,
        "out_sdf": str(out_sdf),
        "log_path": str(log_path),
        "elapsed_sec": elapsed,
        "returncode": proc.returncode,
    }


def patch_dossier_dock_scores(
    scores: dict[str, float],
    *,
    receptor_pdb: str = DEFAULT_TEM1_PDB,
) -> dict[str, Any]:
    """Write GNINA CNN affinities into compound_dossiers.json."""
    if not COMPOUND_DOSSIERS_JSON.exists():
        return {"status": "missing", "path": str(COMPOUND_DOSSIERS_JSON), "patched": 0}

    payload = json.loads(COMPOUND_DOSSIERS_JSON.read_text())
    compounds = payload.setdefault("compounds", {})
    patched = 0
    for compound_id, affinity in scores.items():
        entry = compounds.setdefault(compound_id, {"compound_id": compound_id})
        docking = entry.setdefault("docking", {})
        docking["receptor"] = receptor_pdb
        docking["gnina_cnn_affinity"] = affinity
        docking.setdefault("poses_local", f"pvjthomas/local/docking/{compound_id}/")
        patched += 1

    payload["updated_at"] = _utc_now()
    COMPOUND_DOSSIERS_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    return {
        "status": "ok",
        "path": str(COMPOUND_DOSSIERS_JSON.relative_to(REPO_ROOT)),
        "patched": patched,
    }


def run_batch_dock(
    compounds: list[dict[str, Any]],
    *,
    receptor_pdb: str = DEFAULT_TEM1_PDB,
    skip_existing: bool = True,
    exhaustiveness: int = 8,
    timeout_sec: int = 600,
) -> dict[str, Any]:
    """Dock a list of library compounds; return per-compound results and dossier patch summary."""
    status = gnina_status()
    if not status["available"]:
        return {
            "status": "missing_binary",
            "message": (
                "GNINA binary not found. Install from https://github.com/gnina/gnina/releases "
                "or set GNINA_BIN to the executable path. See scripts/install-gnina.sh."
            ),
            "gnina": status,
        }
    if not RDKIT_AVAILABLE:
        return {
            "status": "missing_rdkit",
            "message": "RDKit is required to embed SMILES before GNINA docking.",
            "gnina": status,
        }

    gnina_bin = status["binary"]
    assert gnina_bin is not None

    try:
        receptor = prepare_receptor(receptor_pdb)
    except RuntimeError as exc:
        return {"status": "receptor_error", "message": str(exc), "gnina": status}

    existing_scores: dict[str, float] = {}
    if skip_existing and COMPOUND_DOSSIERS_JSON.exists():
        dossiers = json.loads(COMPOUND_DOSSIERS_JSON.read_text())
        for cid, entry in dossiers.get("compounds", {}).items():
            affinity = entry.get("docking", {}).get("gnina_cnn_affinity")
            if affinity is not None:
                existing_scores[cid] = float(affinity)

    results: list[dict[str, Any]] = []
    new_scores: dict[str, float] = dict(existing_scores)

    for compound in compounds:
        compound_id = str(compound["compound_id"])
        if skip_existing and compound_id in existing_scores:
            results.append(
                {
                    "compound_id": compound_id,
                    "status": "skipped_existing",
                    "gnina_cnn_affinity": existing_scores[compound_id],
                }
            )
            continue

        smiles = compound.get("smiles") or ""
        out_dir = LOCAL_DOCKING / compound_id
        ligand_sdf = out_dir / "ligand.sdf"
        if not smiles_to_sdf(smiles, ligand_sdf):
            results.append(
                {
                    "compound_id": compound_id,
                    "status": "bad_smiles",
                    "smiles": smiles,
                }
            )
            continue

        dock_result = run_gnina_dock(
            gnina_bin=gnina_bin,
            receptor_pdb=receptor["receptor_pdb"],
            autobox_ligand_pdb=receptor["autobox_ligand_pdb"],
            ligand_sdf=ligand_sdf,
            out_dir=out_dir,
            exhaustiveness=exhaustiveness,
            timeout_sec=timeout_sec,
        )
        row = {"compound_id": compound_id, **dock_result}
        results.append(row)
        affinity = dock_result.get("gnina_cnn_affinity")
        if affinity is not None:
            new_scores[compound_id] = float(affinity)

    patch_summary = patch_dossier_dock_scores(new_scores, receptor_pdb=receptor_pdb)
    ok_count = sum(1 for r in results if r.get("status") == "ok")
    skipped = sum(1 for r in results if r.get("status") == "skipped_existing")

    return {
        "status": "ok" if ok_count or skipped else "no_scores",
        "requested_pdb": receptor_pdb,
        "receptor_pdb": receptor.get("effective_pdb", receptor_pdb),
        "alias_note": receptor.get("alias_note"),
        "autobox_residue": receptor.get("autobox_residue"),
        "receptor_cache": str(receptor["receptor_pdb"]),
        "autobox_ligand": str(receptor["autobox_ligand_pdb"]),
        "docked": ok_count,
        "skipped_existing": skipped,
        "failed": sum(
            1
            for r in results
            if r.get("status") not in {"ok", "skipped_existing"}
        ),
        "scores_in_dossiers": len(new_scores),
        "dossiers": patch_summary,
        "results": results,
        "poses_local": str(LOCAL_DOCKING),
        "gnina": status,
    }
