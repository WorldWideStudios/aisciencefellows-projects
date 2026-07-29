"""Unit tests for GNINA docking helpers (mocked subprocess, no GPU)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from agent.tools import docking as docking_mod


@pytest.fixture
def docking_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    local = tmp_path / "pvjthomas" / "local" / "docking"
    receptor_dir = local / "_receptor"
    data = tmp_path / "data"
    data.mkdir()
    dossiers = {
        "schema_version": 1,
        "compounds": {
            "T0138": {
                "compound_id": "T0138",
                "docking": {"receptor": "1JQL", "gnina_cnn_affinity": None},
            }
        },
    }
    dossiers_path = data / "compound_dossiers.json"
    dossiers_path.write_text(json.dumps(dossiers, indent=2) + "\n")

    monkeypatch.setattr(docking_mod, "LOCAL_DOCKING", local)
    monkeypatch.setattr(docking_mod, "DOCKING_RECEPTOR_DIR", receptor_dir)
    monkeypatch.setattr(docking_mod, "COMPOUND_DOSSIERS_JSON", dossiers_path)
    monkeypatch.setattr(docking_mod, "REPO_ROOT", tmp_path)
    return tmp_path, dossiers_path, local


def test_prepare_receptor_splits_protein_and_ligand(docking_workspace, tmp_path: Path) -> None:
    _, _, local = docking_workspace
    pdb = local / "_receptor" / "TEST.pdb"
    pdb.parent.mkdir(parents=True, exist_ok=True)
    pdb.write_text(
        "\n".join(
            [
                "ATOM      1  N   ALA A   1      10.000  20.000  30.000  1.00 50.00           N",
                "HETATM    1  C1  LIG A 999      11.000  21.000  31.000  1.00 50.00           C",
                "HETATM    2  C2  LIG A 999      12.000  22.000  32.000  1.00 50.00           C",
                "HETATM    3  O   HOH A 998      13.000  23.000  33.000  1.00 50.00           O",
            ]
        )
        + "\n"
    )

    with patch.object(docking_mod, "fetch_pdb", return_value=pdb):
        prepared = docking_mod.prepare_receptor("TEST", work_dir=local / "_receptor")
    receptor_text = prepared["receptor_pdb"].read_text()
    autobox_text = prepared["autobox_ligand_pdb"].read_text()

    assert "ATOM" in receptor_text
    assert "HETATM" not in receptor_text
    assert "LIG" in autobox_text
    assert "HOH" not in autobox_text
    assert prepared["autobox_residue"] == "LIG"


def test_resolve_receptor_pdb_maps_1jql_alias() -> None:
    effective, note = docking_mod.resolve_receptor_pdb("1JQL")
    assert effective == "1XPB"
    assert note is not None


def test_prepare_receptor_1jql_alias_downloads_tem1(docking_workspace) -> None:
    _, _, local = docking_workspace
    prepared = docking_mod.prepare_receptor("1JQL", work_dir=local / "_receptor")
    assert prepared["requested_pdb"] == "1JQL"
    assert prepared["effective_pdb"] == "1XPB"
    assert prepared["autobox_residue"] == "SO4"
    assert prepared["receptor_pdb"].exists()


def test_patch_dossier_dock_scores(docking_workspace) -> None:
    _, dossiers_path, _ = docking_workspace
    summary = docking_mod.patch_dossier_dock_scores({"T0138": -7.2}, receptor_pdb="1JQL")
    payload = json.loads(dossiers_path.read_text())

    assert summary["patched"] == 1
    assert payload["compounds"]["T0138"]["docking"]["gnina_cnn_affinity"] == -7.2


def test_run_batch_dock_missing_binary(docking_workspace) -> None:
    with patch.object(docking_mod, "resolve_gnina_binary", return_value=None):
        result = docking_mod.run_batch_dock(
            [{"compound_id": "T0138", "smiles": "CCO"}],
            receptor_pdb="1JQL",
        )
    assert result["status"] == "missing_binary"


def test_run_batch_dock_mocked_gnina(docking_workspace) -> None:
    _, dossiers_path, local = docking_workspace
    receptor_dir = local / "_receptor"
    receptor_dir.mkdir(parents=True, exist_ok=True)
    (receptor_dir / "1XPB.pdb").write_text(
        "ATOM      1  N   ALA A   1      10.000  20.000  30.000  1.00 50.00           N\n"
        "HETATM    1  S   SO4 A 500      11.000  21.000  31.000  1.00 50.00           S\n"
    )

    def fake_dock(**kwargs):
        out_dir = kwargs["out_dir"]
        out_sdf = out_dir / "docked.sdf"
        out_sdf.write_text("mock\n")
        return {
            "status": "ok",
            "gnina_cnn_affinity": -6.5,
            "out_sdf": str(out_sdf),
            "log_path": str(out_dir / "gnina.log"),
            "elapsed_sec": 1.0,
            "returncode": 0,
        }

    compounds = [
        {
            "compound_id": "T0138",
            "smiles": "CC(=O)O",
        }
    ]

    with (
        patch.object(docking_mod, "resolve_gnina_binary", return_value="/usr/bin/gnina"),
        patch.object(docking_mod, "run_gnina_dock", side_effect=fake_dock),
    ):
        result = docking_mod.run_batch_dock(compounds, receptor_pdb="1JQL", skip_existing=False)

    assert result["status"] == "ok"
    assert result["docked"] == 1
    payload = json.loads(dossiers_path.read_text())
    assert payload["compounds"]["T0138"]["docking"]["gnina_cnn_affinity"] == -6.5
