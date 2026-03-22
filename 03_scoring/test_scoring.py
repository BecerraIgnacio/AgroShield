"""Tests for scoring functions."""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.properties import (
    compute_all_properties,
    hydrophobic_moment,
    hydrophobic_ratio,
    instability_index,
    net_charge,
)
from scripts.scoring import (
    activity_score,
    combined_score,
    score_candidates,
    stability_score,
    synthesizability_score,
)
from scripts.toxicity import hemolytic_score, phytotoxicity_score


# --- Properties ---

class TestProperties:
    def test_net_charge_positive(self):
        # Poly-lysine should be highly positive
        charge = net_charge("KKKKKK")
        assert charge > 4.0

    def test_net_charge_negative(self):
        charge = net_charge("DDDDDD")
        assert charge < -4.0

    def test_hydrophobic_ratio(self):
        assert hydrophobic_ratio("AAAAA") == 1.0  # all hydrophobic
        assert hydrophobic_ratio("KKKKK") == 0.0  # none hydrophobic

    def test_hydrophobic_ratio_mixed(self):
        ratio = hydrophobic_ratio("AKAK")
        assert 0.4 < ratio < 0.6

    def test_instability_index_type(self):
        ii = instability_index("GIGKFLHSAKKFGKAFVGEIMNS")
        assert isinstance(ii, float)

    def test_hydrophobic_moment_returns_float(self):
        hm = hydrophobic_moment("GIGKFLHSAKKFGKAFVGEIMNS")
        assert isinstance(hm, float)
        assert hm >= 0.0

    def test_compute_all_properties_keys(self):
        props = compute_all_properties("GIGKFLHSAKKFGKAFVGEIMNS")
        expected_keys = {
            "charge", "hydrophobic_ratio", "instability_index",
            "molecular_weight", "aromaticity", "gravy", "hydrophobic_moment",
        }
        assert set(props.keys()) == expected_keys


# --- Toxicity ---

class TestToxicity:
    def test_hemolytic_score_range(self):
        score = hemolytic_score("GIGKFLHSAKKFGKAFVGEIMNS")
        assert 0.0 <= score <= 1.0

    def test_phytotoxicity_score_range(self):
        score = phytotoxicity_score("GIGKFLHSAKKFGKAFVGEIMNS")
        assert 0.0 <= score <= 1.0

    def test_short_cationic_low_phyto(self):
        # Short, moderately cationic → should have low phytotoxicity
        score = phytotoxicity_score("KKLLKKLLKK")
        assert score < 0.5

    def test_long_peptide_higher_phyto(self):
        short_score = phytotoxicity_score("KKLLKK")
        long_score = phytotoxicity_score("KKLLKK" * 6)
        assert long_score >= short_score


# --- Scoring ---

class TestScoring:
    def test_activity_score_clamp(self):
        assert activity_score(1.5) == 1.0
        assert activity_score(-0.1) == 0.0
        assert activity_score(0.8) == 0.8

    def test_stability_score_stable(self):
        # Magainin-2 analog — should be somewhat stable
        score = stability_score("GIGKFLHSAKKFGKAFVGEIMNS")
        assert 0.0 <= score <= 1.0

    def test_stability_score_range(self):
        score = stability_score("AAAAAA")
        assert 0.0 <= score <= 1.0

    def test_synthesizability_short_simple(self):
        score = synthesizability_score("AKAKAKAK")
        assert score > 0.8

    def test_synthesizability_cysteine_penalty(self):
        no_cys = synthesizability_score("AKAKAKAK")
        many_cys = synthesizability_score("ACCCCKCCAK")
        assert many_cys < no_cys

    def test_synthesizability_proline_penalty(self):
        no_pp = synthesizability_score("AKPAKPAK")
        with_pp = synthesizability_score("AKPPAKAK")
        assert with_pp < no_pp

    def test_combined_score_range(self):
        c = combined_score(0.8, 0.2, 0.1, 0.7, 0.9)
        assert 0.0 <= c <= 1.0

    def test_combined_score_perfect(self):
        c = combined_score(1.0, 0.0, 0.0, 1.0, 1.0)
        assert c == pytest.approx(1.0)

    def test_score_candidates_output_columns(self):
        df = pd.DataFrame({
            "id": ["TEST_001", "TEST_002"],
            "sequence": ["GIGKFLHSAKKFGKAFVGEIMNS", "KKLLKKLLKK"],
            "length": [23, 10],
            "amp_probability": [0.9, 0.7],
        })
        result = score_candidates(df)
        expected_cols = {
            "id", "sequence", "length", "charge",
            "activity_score", "hemolytic_score", "phytotoxicity_score",
            "stability_score", "synthesizability_score", "combined_score", "rank",
        }
        assert set(result.columns) == expected_cols

    def test_score_candidates_sorted_descending(self):
        df = pd.DataFrame({
            "id": ["A", "B", "C"],
            "sequence": ["KKKKKK", "AAAAAA", "GIGKFLHSAKKFGKAFVGEIMNS"],
            "length": [6, 6, 23],
            "amp_probability": [0.9, 0.3, 0.8],
        })
        result = score_candidates(df)
        scores = result["combined_score"].tolist()
        assert scores == sorted(scores, reverse=True)

    def test_score_candidates_rank(self):
        df = pd.DataFrame({
            "id": ["A", "B"],
            "sequence": ["KKKKKK", "AAAAAA"],
            "length": [6, 6],
            "amp_probability": [0.9, 0.3],
        })
        result = score_candidates(df)
        assert result["rank"].tolist() == [1, 2]
