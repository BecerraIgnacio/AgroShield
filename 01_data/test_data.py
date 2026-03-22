"""Tests for Phase 1 data pipeline integrity."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

DATA_DIR = Path(__file__).resolve().parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
VALID_AAS = set("ACDEFGHIKLMNPQRSTVWY")

REQUIRED_AMP_COLS = {"id", "sequence", "length", "source_db", "target_organisms", "activity", "mic_um"}
VALID_ACTIVITIES = {"antibacterial", "antifungal", "broad-spectrum"}
MIN_AMP_COUNT = 500


@pytest.fixture
def amps_df() -> pd.DataFrame:
    path = PROCESSED_DIR / "amps_unified.csv"
    assert path.exists(), f"Missing {path} — run the pipeline first"
    df = pd.read_csv(path)
    df["target_organisms"] = df["target_organisms"].apply(
        lambda x: str(x).split(";") if pd.notna(x) else []
    )
    return df


@pytest.fixture
def pathogen_map() -> dict:
    path = PROCESSED_DIR / "pathogen_crop_map.json"
    assert path.exists(), f"Missing {path} — run build_pathogen_db.py first"
    return json.loads(path.read_text())


class TestAMPDataset:
    def test_minimum_count(self, amps_df: pd.DataFrame) -> None:
        assert len(amps_df) >= MIN_AMP_COUNT, f"Only {len(amps_df)} AMPs, need >= {MIN_AMP_COUNT}"

    def test_required_columns(self, amps_df: pd.DataFrame) -> None:
        missing = REQUIRED_AMP_COLS - set(amps_df.columns)
        assert not missing, f"Missing columns: {missing}"

    def test_no_duplicate_ids(self, amps_df: pd.DataFrame) -> None:
        dupes = amps_df[amps_df["id"].duplicated()]
        assert dupes.empty, f"Duplicate IDs: {dupes['id'].tolist()[:10]}"

    def test_no_duplicate_sequences(self, amps_df: pd.DataFrame) -> None:
        dupes = amps_df[amps_df["sequence"].duplicated()]
        assert dupes.empty, f"{len(dupes)} duplicate sequences found"

    def test_valid_sequences(self, amps_df: pd.DataFrame) -> None:
        for _, row in amps_df.iterrows():
            seq = row["sequence"]
            assert isinstance(seq, str) and len(seq) >= 5, f"Invalid sequence for {row['id']}"
            invalid = set(seq) - VALID_AAS
            assert not invalid, f"Invalid AAs {invalid} in {row['id']}: {seq}"

    def test_length_matches_sequence(self, amps_df: pd.DataFrame) -> None:
        mismatches = amps_df[amps_df["length"] != amps_df["sequence"].str.len()]
        assert mismatches.empty, f"Length mismatches: {mismatches['id'].tolist()[:5]}"

    def test_valid_activities(self, amps_df: pd.DataFrame) -> None:
        invalid = set(amps_df["activity"].unique()) - VALID_ACTIVITIES
        assert not invalid, f"Invalid activities: {invalid}"

    def test_mic_values_positive(self, amps_df: pd.DataFrame) -> None:
        mic_valid = amps_df["mic_um"].dropna()
        assert (mic_valid > 0).all(), "Found non-positive MIC values"

    def test_target_organisms_not_empty(self, amps_df: pd.DataFrame) -> None:
        empty = amps_df[amps_df["target_organisms"].apply(lambda x: len(x) == 0 or x == [""])]
        assert len(empty) < len(amps_df) * 0.1, f"Too many entries with empty targets: {len(empty)}"

    def test_has_real_amps(self, amps_df: pd.DataFrame) -> None:
        real_ids = amps_df[amps_df["id"].str.startswith("AMP_REAL_")]
        assert len(real_ids) >= 10, "Should contain known real AMP sequences"

    def test_has_synthetic_amps(self, amps_df: pd.DataFrame) -> None:
        syn_ids = amps_df[amps_df["id"].str.startswith("AMP_SYN_")]
        assert len(syn_ids) >= 400

    def test_valid_source_dbs(self, amps_df: pd.DataFrame) -> None:
        valid = {"DRAMP", "APD3", "dbAMP", "UniProt"}
        sources = set(amps_df["source_db"].unique())
        assert sources.issubset(valid), f"Unexpected sources: {sources - valid}"

    def test_mic_values_under_1000(self, amps_df: pd.DataFrame) -> None:
        mic_valid = amps_df["mic_um"].dropna()
        assert (mic_valid < 1000).all(), "MIC values should be < 1000 uM"


class TestPathogenMap:
    REQUIRED_PATHOGENS = [
        "Fusarium oxysporum", "Xanthomonas campestris", "Botrytis cinerea",
        "Pseudomonas syringae", "Magnaporthe oryzae", "Puccinia graminis",
        "Ralstonia solanacearum",
    ]

    def test_required_pathogens_present(self, pathogen_map: dict) -> None:
        missing = [p for p in self.REQUIRED_PATHOGENS if p not in pathogen_map]
        assert not missing, f"Missing required pathogens: {missing}"

    def test_pathogen_has_crops(self, pathogen_map: dict) -> None:
        for name, info in pathogen_map.items():
            assert "crops" in info and len(info["crops"]) > 0, f"{name} has no crops"

    def test_pathogen_has_kingdom(self, pathogen_map: dict) -> None:
        for name, info in pathogen_map.items():
            assert "kingdom" in info, f"{name} missing kingdom"
            assert info["kingdom"] in {"fungi", "bacteria", "oomycete"}, f"{name} invalid kingdom: {info['kingdom']}"

    def test_pathogen_has_description(self, pathogen_map: dict) -> None:
        for name, info in pathogen_map.items():
            assert "description" in info and len(info["description"]) > 10, f"{name} missing description"

    def test_pathogen_has_economic_impact(self, pathogen_map: dict) -> None:
        for name, info in pathogen_map.items():
            assert "economic_impact" in info and len(info["economic_impact"]) > 20, (
                f"{name} missing or short economic_impact"
            )


class TestPipelineFunctions:
    def test_clean_sequence_valid(self) -> None:
        from scripts.preprocess import clean_sequence
        assert clean_sequence("ACDEFGHIKLMNPQRSTVWY") == "ACDEFGHIKLMNPQRSTVWY"

    def test_clean_sequence_lowercase(self) -> None:
        from scripts.preprocess import clean_sequence
        assert clean_sequence("acdefg") == "ACDEFG"

    def test_clean_sequence_whitespace(self) -> None:
        from scripts.preprocess import clean_sequence
        assert clean_sequence("ACD EFG") == "ACDEFG"

    def test_clean_sequence_invalid_chars(self) -> None:
        from scripts.preprocess import clean_sequence
        assert clean_sequence("ABCJ") is None  # B and J are not standard AAs

    def test_clean_sequence_too_short(self) -> None:
        from scripts.preprocess import clean_sequence
        assert clean_sequence("ACK") is None

    def test_generate_synthetic_deterministic(self) -> None:
        from scripts.fetch_amps import generate_synthetic_amps
        df1 = generate_synthetic_amps(n=50, seed=123)
        df2 = generate_synthetic_amps(n=50, seed=123)
        assert df1["sequence"].tolist() == df2["sequence"].tolist()

    def test_build_pathogen_db(self) -> None:
        from scripts.build_pathogen_db import build_pathogen_crop_map
        mapping = build_pathogen_crop_map()
        assert isinstance(mapping, dict)
        assert len(mapping) >= 7
