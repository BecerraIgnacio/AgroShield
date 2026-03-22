"""Pipeline orchestration — calls phases 1-3 and returns scored candidates."""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "01_data"))
sys.path.insert(0, str(ROOT / "02_model"))
sys.path.insert(0, str(ROOT / "03_scoring"))

PATHOGEN_MAP_PATH = ROOT / "01_data" / "data" / "processed" / "pathogen_crop_map.json"
AMPS_PATH = ROOT / "01_data" / "data" / "processed" / "amps_unified.csv"
SCORED_ALL_PATH = ROOT / "03_scoring" / "output" / "scored_all.csv"
TOP_CANDIDATES_PATH = ROOT / "03_scoring" / "output" / "top_candidates.csv"
GENERATED_CANDIDATES_PATH = ROOT / "02_model" / "models" / "generated_candidates.csv"


def generated_candidates_count() -> int:
    if GENERATED_CANDIDATES_PATH.exists():
        with open(GENERATED_CANDIDATES_PATH) as f:
            return sum(1 for _ in f) - 1
    return 0


def load_pathogen_map() -> dict:
    import json
    with open(PATHOGEN_MAP_PATH) as f:
        return json.load(f)


def load_precomputed_results() -> pd.DataFrame | None:
    if SCORED_ALL_PATH.exists():
        return pd.read_csv(SCORED_ALL_PATH)
    return None


def load_reference_amps() -> pd.DataFrame:
    return pd.read_csv(AMPS_PATH)


def run_full_pipeline(pathogen: str, n_candidates: int = 20) -> pd.DataFrame:
    from scripts.generate_peptides import generate_for_pathogen
    from scripts.scoring import score_candidates

    candidates = generate_for_pathogen(pathogen, min_candidates=max(n_candidates * 3, 50))
    if candidates.empty:
        return candidates

    scored = score_candidates(candidates)
    return scored.head(n_candidates).reset_index(drop=True)
