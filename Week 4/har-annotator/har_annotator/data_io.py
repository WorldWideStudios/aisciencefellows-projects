"""Load the HAR base table and the Cui 2025 supplementary sheets."""
from __future__ import annotations

import pandas as pd

from . import download as dl
from .filters import MAIN_CHROMS

# Source: Cui et al. 2025, Nature (doi:10.1038/s41586-025-08622), Supplementary
# Table 4, redistributed via github.com/athenamarou/HAR-TFBS-Project.
CUI_SUPP4_URL = ("https://raw.githubusercontent.com/athenamarou/HAR-TFBS-Project/"
                 "main/data/supplementary/41586_2025_8622_MOESM4_ESM.xlsx")


def _supp4() -> str:
    return str(dl.fetch(CUI_SUPP4_URL, "cui2025_supp4", "cui2025_HAR_supp4.xlsx"))


def load_hars() -> pd.DataFrame:
    """HAR base table: coords (hg38), Cui cross-reference IDs, width."""
    info = pd.read_excel(_supp4(), sheet_name="HARs information", header=2)
    info.columns = [str(c).strip() for c in info.columns]
    info = info.rename(columns={"Names": "har_id", "Other Names": "har_alt_id",
                                "chr_hg38": "chrom", "start_hg38": "start",
                                "end_hg38": "end"})
    hars = info[["har_id", "har_alt_id", "chrom", "start", "end"]].copy()
    hars = hars[hars.chrom.isin(MAIN_CHROMS)].copy()
    hars["start"] = hars.start.astype(int)
    hars["end"] = hars.end.astype(int)
    hars["width"] = hars.end - hars.start
    return hars.reset_index(drop=True)


def load_plac_interaction_table() -> pd.DataFrame:
    """Cui 2025 neuronal PLAC-seq 'HARs interacting genes' sheet (raw)."""
    ig = pd.read_excel(_supp4(), sheet_name="HARs interacting genes", header=2)
    ig.columns = [str(c).strip() for c in ig.columns]
    return ig
