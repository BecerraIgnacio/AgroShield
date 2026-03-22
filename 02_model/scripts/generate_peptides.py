"""Generate novel AMP candidates via mutation-based and interpolation strategies."""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from .embeddings import generate_embeddings, get_esm2_model, load_cache
from .train_classifier import load_classifier

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "01_data" / "data" / "processed"
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

VALID_AAS = list("ACDEFGHIKLMNPQRSTVWY")
MIN_LENGTH = 10
MAX_LENGTH = 50
SCORE_THRESHOLD = 0.7
MIN_CANDIDATES = 50
RANDOM_STATE = 42


def load_pathogen_map(path: Path | None = None) -> dict:
    """Load pathogen-crop mapping."""
    import json
    p = path or DATA_DIR / "pathogen_crop_map.json"
    with open(p) as f:
        return json.load(f)


def get_seed_amps(
    pathogen: str,
    df: pd.DataFrame,
    top_n: int = 20,
) -> pd.DataFrame:
    """Get top AMPs targeting a specific pathogen."""
    # Filter for AMPs active against this pathogen
    mask = df["target_organisms"].str.contains(pathogen, case=False, na=False)
    hits = df[mask].copy()

    # If not enough hits, also include AMPs with same activity type
    if len(hits) < 5:
        # Determine activity type from pathogen kingdom
        pathogen_map = load_pathogen_map()
        kingdom = "bacteria"
        for name, info in pathogen_map.items():
            if pathogen.lower() in name.lower():
                kingdom = info.get("kingdom", "bacteria")
                break
        activity = "antifungal" if kingdom == "fungi" else "antibacterial"
        activity_mask = df["activity"] == activity
        hits = pd.concat([hits, df[activity_mask]]).drop_duplicates(subset="id")

    # Prefer those with lower MIC (more potent)
    hits = hits.sort_values("mic_um", ascending=True, na_position="last")
    return hits.head(top_n)


def mutate_sequence(
    sequence: str,
    n_mutations: int = 1,
    rng: random.Random | None = None,
) -> str:
    """Apply random point mutations to a sequence."""
    rng = rng or random.Random()
    chars = list(sequence)
    positions = rng.sample(range(len(chars)), min(n_mutations, len(chars)))
    for pos in positions:
        original = chars[pos]
        candidates = [aa for aa in VALID_AAS if aa != original]
        chars[pos] = rng.choice(candidates)
    return "".join(chars)


def generate_mutations(
    seed_sequences: list[str],
    n_variants_per_seed: int = 10,
    max_mutations: int = 3,
    seed: int = RANDOM_STATE,
) -> list[str]:
    """Generate mutation-based variants from seed sequences."""
    rng = random.Random(seed)
    variants: set[str] = set()

    for seq in seed_sequences:
        if len(seq) < MIN_LENGTH or len(seq) > MAX_LENGTH:
            continue
        for _ in range(n_variants_per_seed):
            n_mut = rng.randint(1, max_mutations)
            variant = mutate_sequence(seq, n_mut, rng)
            if MIN_LENGTH <= len(variant) <= MAX_LENGTH:
                variants.add(variant)

    # Remove any that are identical to seeds
    variants -= set(seed_sequences)
    return list(variants)


def generate_interpolated(
    seed_sequences: list[str],
    all_sequences: list[str],
    all_embeddings: np.ndarray,
    tokenizer=None,
    model=None,
    n_interpolations: int = 30,
    seed: int = RANDOM_STATE,
) -> list[str]:
    """Generate candidates by interpolating between seed AMP embeddings."""
    rng = random.Random(seed)

    if tokenizer is None or model is None:
        tokenizer, model = get_esm2_model()

    # Embed seeds
    seed_embeddings = generate_embeddings(seed_sequences, tokenizer, model)

    # Generate interpolated embeddings
    interpolated: list[np.ndarray] = []
    for _ in range(n_interpolations):
        i, j = rng.sample(range(len(seed_embeddings)), 2)
        alpha = rng.uniform(0.3, 0.7)
        interp = alpha * seed_embeddings[i] + (1 - alpha) * seed_embeddings[j]
        interpolated.append(interp)

    if not interpolated:
        return []

    interp_matrix = np.vstack(interpolated)

    # Find nearest real sequences to interpolated embeddings
    sims = cosine_similarity(interp_matrix, all_embeddings)
    nearest_indices = sims.argmax(axis=1)

    # Use nearest sequences as generation seeds, then mutate
    candidates: set[str] = set()
    for idx in nearest_indices:
        seq = all_sequences[idx]
        if MIN_LENGTH <= len(seq) <= MAX_LENGTH:
            for n_mut in range(1, 4):
                variant = mutate_sequence(seq, n_mut, rng)
                candidates.add(variant)

    candidates -= set(all_sequences)
    return list(candidates)


def score_candidates(
    candidates: list[str],
    clf,
    tokenizer=None,
    model=None,
    threshold: float = SCORE_THRESHOLD,
) -> pd.DataFrame:
    """Score candidate peptides with classifier, filter by threshold."""
    if tokenizer is None or model is None:
        tokenizer, model = get_esm2_model()

    embeddings = generate_embeddings(candidates, tokenizer, model)
    probabilities = clf.predict_proba(embeddings)[:, 1]

    results = pd.DataFrame({
        "sequence": candidates,
        "length": [len(s) for s in candidates],
        "amp_probability": probabilities,
    })

    # Filter by threshold
    results = results[results["amp_probability"] >= threshold].copy()
    results = results.sort_values("amp_probability", ascending=False).reset_index(drop=True)
    results["id"] = [f"GEN_{i:04d}" for i in range(len(results))]
    return results[["id", "sequence", "length", "amp_probability"]]


def generate_for_pathogen(
    pathogen: str,
    min_candidates: int = MIN_CANDIDATES,
    threshold: float = SCORE_THRESHOLD,
) -> pd.DataFrame:
    """Full generation pipeline for a given pathogen."""
    # Load data
    df = pd.read_csv(DATA_DIR / "amps_unified.csv")
    cache = load_cache()
    all_sequences = cache["sequences"].tolist()
    all_embeddings = cache["embeddings"]

    # Load models
    tokenizer, model = get_esm2_model()
    clf = load_classifier()

    # Get seed AMPs
    seeds_df = get_seed_amps(pathogen, df)
    seed_sequences = seeds_df["sequence"].tolist()

    if not seed_sequences:
        raise ValueError(f"No seed AMPs found for pathogen: {pathogen}")

    # Generate via mutations
    mutation_candidates = generate_mutations(seed_sequences, n_variants_per_seed=15)

    # Generate via interpolation
    interp_candidates = generate_interpolated(
        seed_sequences, all_sequences, all_embeddings, tokenizer, model
    )

    # Combine and deduplicate
    all_candidates = list(set(mutation_candidates + interp_candidates))

    # Score and filter
    if not all_candidates:
        raise ValueError("No candidates generated")

    results = score_candidates(all_candidates, clf, tokenizer, model, threshold)

    # If not enough, lower threshold progressively
    current_threshold = threshold
    while len(results) < min_candidates and current_threshold > 0.5:
        current_threshold -= 0.05
        results = score_candidates(all_candidates, clf, tokenizer, model, current_threshold)

    return results


def main() -> None:
    import json

    pathogen_map = load_pathogen_map()
    first_pathogen = next(iter(pathogen_map))

    print(f"Generating AMP candidates for: {first_pathogen}")
    results = generate_for_pathogen(first_pathogen)
    print(f"  Generated {len(results)} candidates (threshold >= {SCORE_THRESHOLD})")
    print(results.head(10).to_string())

    # Save results
    out = MODELS_DIR / "generated_candidates.csv"
    results.to_csv(out, index=False)
    print(f"  Saved to {out}")


if __name__ == "__main__":
    main()
