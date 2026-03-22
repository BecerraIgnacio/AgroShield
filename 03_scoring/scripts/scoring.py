"""Main scoring pipeline: multi-dimensional ranking of peptide candidates."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .properties import (
    hydrophobic_ratio,
    instability_index,
    net_charge,
)
from .toxicity import hemolytic_score, phytotoxicity_score

CANDIDATES_FILE = Path(__file__).resolve().parent.parent.parent / "02_model" / "models" / "generated_candidates.csv"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
TOP_N = 20

# Weights from CLAUDE.md spec
W_ACTIVITY = 0.35
W_HEMOLYTIC = 0.25
W_PHYTO = 0.15
W_STABILITY = 0.15
W_SYNTH = 0.10


def activity_score(amp_probability: float) -> float:
    """Activity score = classifier probability (already 0-1)."""
    return max(0.0, min(1.0, amp_probability))


def stability_score(sequence: str) -> float:
    """Stability score based on instability index.

    Instability index < 40 → stable. Normalize to 0-1 where 1 = most stable.
    """
    ii = instability_index(sequence)
    if ii <= 0:
        return 1.0
    if ii >= 80:
        return 0.0
    return max(0.0, 1.0 - ii / 80.0)


def synthesizability_score(sequence: str) -> float:
    """Synthesizability based on length, cysteine count, and proline runs."""
    length = len(sequence)
    score = 1.0

    # Length penalty: shorter is easier
    if length > 30:
        score -= min((length - 30) / 20, 0.4)

    # Cysteine penalty: >2 cysteines → disulfide complexity
    cys_count = sequence.count("C")
    if cys_count > 2:
        score -= min((cys_count - 2) * 0.1, 0.3)

    # Consecutive proline penalty
    if "PP" in sequence:
        score -= 0.15
    if "PPP" in sequence:
        score -= 0.10

    # Rare amino acid penalty (unusual in synthesis)
    rare = sum(1 for aa in sequence if aa in "MW")
    if rare > 3:
        score -= min((rare - 3) * 0.05, 0.2)

    return max(0.0, min(1.0, score))


def combined_score(
    activity: float,
    hemolytic: float,
    phytotoxicity: float,
    stability: float,
    synthesizability: float,
) -> float:
    """Weighted combined score per CLAUDE.md formula."""
    return (
        W_ACTIVITY * activity
        + W_HEMOLYTIC * (1 - hemolytic)
        + W_PHYTO * (1 - phytotoxicity)
        + W_STABILITY * stability
        + W_SYNTH * synthesizability
    )


def score_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Score all candidates and return ranked DataFrame."""
    records = []
    for _, row in df.iterrows():
        seq = row["sequence"]
        act = activity_score(row["amp_probability"])
        hemo = hemolytic_score(seq)
        phyto = phytotoxicity_score(seq)
        stab = stability_score(seq)
        synth = synthesizability_score(seq)
        comb = combined_score(act, hemo, phyto, stab, synth)

        records.append({
            "id": row["id"],
            "sequence": seq,
            "length": len(seq),
            "charge": round(net_charge(seq), 2),
            "activity_score": round(act, 4),
            "hemolytic_score": round(hemo, 4),
            "phytotoxicity_score": round(phyto, 4),
            "stability_score": round(stab, 4),
            "synthesizability_score": round(synth, 4),
            "combined_score": round(comb, 4),
        })

    result = pd.DataFrame(records)
    result = result.sort_values("combined_score", ascending=False).reset_index(drop=True)
    result["rank"] = result.index + 1
    return result


def run_pipeline(
    candidates_path: Path | None = None,
    top_n: int = TOP_N,
) -> pd.DataFrame:
    """Load candidates, score them, save and return top N."""
    path = candidates_path or CANDIDATES_FILE
    df = pd.read_csv(path)
    scored = score_candidates(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scored.to_csv(OUTPUT_DIR / "scored_all.csv", index=False)
    top = scored.head(top_n)
    top.to_csv(OUTPUT_DIR / "top_candidates.csv", index=False)

    return top


def main() -> None:
    print("Running scoring pipeline...")
    top = run_pipeline()
    print(f"\nTop {len(top)} candidates:")
    print(top[["rank", "id", "sequence", "combined_score", "activity_score",
               "hemolytic_score", "stability_score"]].to_string(index=False))
    print(f"\nResults saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
