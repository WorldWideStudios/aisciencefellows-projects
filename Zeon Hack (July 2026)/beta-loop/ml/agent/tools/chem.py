"""Shared RDKit helpers for reverse and bridge tools."""

from __future__ import annotations

import re
from typing import Any

RDKIT_AVAILABLE = False

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem

    RDKIT_AVAILABLE = True
except (ImportError, AttributeError, ModuleNotFoundError):
    RDKIT_AVAILABLE = False


def rdkit_status() -> dict[str, Any]:
    return {"available": RDKIT_AVAILABLE}


def normalize_name(name: str) -> str:
    text = name.lower().strip()
    for suffix in (
        " sodium",
        " lithium",
        " hydrate",
        " monohydrate",
        " dihydrate",
        " trihydrate",
        " sodium salt",
        " acid",
    ):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_smiles(smiles: str):
    if not RDKIT_AVAILABLE or not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolFromSmiles(Chem.MolToSmiles(mol))


def morgan_fp(mol):
    if not RDKIT_AVAILABLE or mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius=2, nBits=2048)


def tanimoto_smiles(smiles_a: str, smiles_b: str) -> float | None:
    if not RDKIT_AVAILABLE:
        return None
    mol_a = parse_smiles(smiles_a)
    mol_b = parse_smiles(smiles_b)
    if mol_a is None or mol_b is None:
        return None
    fp_a = morgan_fp(mol_a)
    fp_b = morgan_fp(mol_b)
    if fp_a is None or fp_b is None:
        return None
    return float(DataStructs.TanimotoSimilarity(fp_a, fp_b))


def smarts_match(smiles: str, smarts: str) -> bool:
    if not RDKIT_AVAILABLE:
        return False
    mol = parse_smiles(smiles)
    if mol is None:
        return False
    pattern = Chem.MolFromSmarts(smarts)
    if pattern is None:
        return False
    return mol.HasSubstructMatch(pattern)
