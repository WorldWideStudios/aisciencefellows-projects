"""Repo paths for agent tools."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ML_ROOT = Path(__file__).resolve().parents[1]
PVJ_ROOT = REPO_ROOT / "pvjthomas"
DATA_DIR = REPO_ROOT / "data"
LITERATURE_DIR = DATA_DIR / "compound_literature"
LITERATURE_REFS_DIR = LITERATURE_DIR / "refs"
LITERATURE_ONLY_REFS_DIR = LITERATURE_REFS_DIR / "_literature_only"
COMPOUNDS_CSV = DATA_DIR / "compounds.csv"
COMPOUND_DOSSIERS_JSON = DATA_DIR / "compound_dossiers.json"
LITERATURE_SUMMARY_JSON = DATA_DIR / "literature_summary.json"
REFERENCE_INHIBITORS_CSV = DATA_DIR / "reference_inhibitors.csv"
SCREENS_DIR = DATA_DIR / "screens"

WORKFLOW_COMPOUND_SELECTION = ML_ROOT / "workflows" / "compound_selection"
SELECTION_STATE_JSON = WORKFLOW_COMPOUND_SELECTION / "state.json"
LITERATURE_SEARCH_CACHE_JSON = WORKFLOW_COMPOUND_SELECTION / "literature_search_cache.json"
SELECTION_DRAFT_PLATE_JSON = WORKFLOW_COMPOUND_SELECTION / "plate_map_r2_draft.json"
SIMILARITY_NEIGHBORS_JSON = WORKFLOW_COMPOUND_SELECTION / "neighbors.json"
FORWARD_SNAPSHOTS_DIR = WORKFLOW_COMPOUND_SELECTION / "snapshots" / "forward"
# Back-compat alias used in tests
FORWARD_RUNS_DIR = FORWARD_SNAPSHOTS_DIR

LOCAL_ROOT = PVJ_ROOT / "local"
LOCAL_LITERATURE = LOCAL_ROOT / "literature"
LOCAL_DOCKING = LOCAL_ROOT / "docking"
DOCKING_RECEPTOR_DIR = LOCAL_DOCKING / "_receptor"
LOCAL_SIMILARITY = LOCAL_ROOT / "similarity"


def screen_snapshot_dir(round_number: int, version: int) -> Path:
    """Path to a frozen physical screen design: data/screens/{round}/v{version}/."""
    return SCREENS_DIR / str(round_number) / f"v{version}"
