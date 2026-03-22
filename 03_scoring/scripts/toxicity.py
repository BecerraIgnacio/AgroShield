"""Toxicity prediction: hemolytic and phytotoxicity scoring."""
from __future__ import annotations

from .properties import hydrophobic_moment, hydrophobic_ratio, net_charge


# --- Hemolytic toxicity ---

def hemolytic_score(sequence: str) -> float:
    """Predict hemolytic toxicity (0-1, higher = more toxic).

    Features: hydrophobic moment, net charge, hydrophobic ratio.
    Hemolytic peptides tend to be highly hydrophobic and amphipathic.
    """
    hm = hydrophobic_moment(sequence)
    charge = net_charge(sequence)
    hr = hydrophobic_ratio(sequence)

    # High hydrophobic moment → hemolytic
    hm_score = min(hm / 0.8, 1.0)

    # Very high hydrophobicity → hemolytic
    hr_score = min(hr / 0.7, 1.0)

    # Highly cationic peptides (>+8) can be hemolytic too
    charge_penalty = max(0.0, (charge - 8) / 10)

    score = 0.45 * hm_score + 0.35 * hr_score + 0.20 * charge_penalty
    return max(0.0, min(1.0, score))


# --- Phytotoxicity ---

def phytotoxicity_score(sequence: str) -> float:
    """Predict phytotoxicity (0-1, higher = more phytotoxic).

    Plant-safe peptides tend to be: shorter (<30 AA), moderately cationic
    (+2 to +6), and have low hydrophobicity.
    """
    length = len(sequence)
    charge = net_charge(sequence)
    hr = hydrophobic_ratio(sequence)

    # Length penalty: longer peptides more likely phytotoxic
    if length <= 25:
        len_score = 0.0
    elif length <= 35:
        len_score = (length - 25) / 10
    else:
        len_score = 1.0

    # Charge: moderate cationic (+2 to +6) is safe; extremes are risky
    if 2 <= charge <= 6:
        charge_score = 0.0
    elif charge < 2:
        charge_score = min((2 - charge) / 5, 1.0)
    else:
        charge_score = min((charge - 6) / 6, 1.0)

    # High hydrophobicity → phytotoxic
    if hr <= 0.4:
        hr_score = 0.0
    else:
        hr_score = min((hr - 0.4) / 0.3, 1.0)

    score = 0.30 * len_score + 0.35 * charge_score + 0.35 * hr_score
    return max(0.0, min(1.0, score))
