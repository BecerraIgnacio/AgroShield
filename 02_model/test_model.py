"""Tests for Phase 2: ML model — embeddings, classifier, generator."""
from __future__ import annotations

import random
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.embeddings import (
    EMBEDDING_DIM,
    embed_batch,
    generate_embeddings,
    get_esm2_model,
    load_cache,
    save_cache,
)
from scripts.train_classifier import (
    generate_negative_sequences,
    prepare_training_data,
    train_classifier,
)
from scripts.generate_peptides import (
    generate_mutations,
    mutate_sequence,
    score_candidates,
    VALID_AAS,
    MIN_LENGTH,
    MAX_LENGTH,
)


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def esm2():
    tokenizer, model = get_esm2_model()
    return tokenizer, model


SAMPLE_SEQUENCES = [
    "GIGKFLHSAKKFGKAFVGEIMNS",
    "GLFDIVKKVVGALGSL",
    "KWCLLSHERGCTCSDTCRNKCLRSGYCHGFCA",
    "ACDEFGHIKLMNPQRSTVWY",
]


# ── Embedding Tests ───────────────────────────────────────────────

class TestEmbeddings:
    def test_embed_batch_shape(self, esm2):
        tokenizer, model = esm2
        embs = embed_batch(SAMPLE_SEQUENCES[:2], tokenizer, model)
        assert embs.shape == (2, EMBEDDING_DIM)

    def test_embed_batch_not_nan(self, esm2):
        tokenizer, model = esm2
        embs = embed_batch(SAMPLE_SEQUENCES[:2], tokenizer, model)
        assert not np.isnan(embs).any()

    def test_generate_embeddings_all(self, esm2):
        tokenizer, model = esm2
        embs = generate_embeddings(SAMPLE_SEQUENCES, tokenizer, model, batch_size=2)
        assert embs.shape == (len(SAMPLE_SEQUENCES), EMBEDDING_DIM)

    def test_different_sequences_different_embeddings(self, esm2):
        tokenizer, model = esm2
        embs = embed_batch(SAMPLE_SEQUENCES[:2], tokenizer, model)
        # Two different sequences should have different embeddings
        assert not np.allclose(embs[0], embs[1])

    def test_cache_roundtrip(self):
        ids = ["A", "B"]
        seqs = ["ACDEF", "GHIKL"]
        embs = np.random.randn(2, EMBEDDING_DIM).astype(np.float32)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test_cache.npz"
            save_cache(ids, seqs, embs, path)
            loaded = load_cache(path)

            assert list(loaded["ids"]) == ids
            assert list(loaded["sequences"]) == seqs
            np.testing.assert_array_almost_equal(loaded["embeddings"], embs)


# ── Classifier Tests ──────────────────────────────────────────────

class TestClassifier:
    def test_negative_generation_count(self):
        positives = SAMPLE_SEQUENCES
        negs = generate_negative_sequences(positives, n_negatives=10)
        assert len(negs) == 10

    def test_negative_sequences_valid(self):
        positives = SAMPLE_SEQUENCES
        negs = generate_negative_sequences(positives, n_negatives=20)
        for seq in negs:
            assert all(c in VALID_AAS for c in seq)
            assert len(seq) > 0

    def test_negatives_differ_from_positives(self):
        positives = SAMPLE_SEQUENCES
        negs = generate_negative_sequences(positives, n_negatives=20, seed=123)
        # At least most negatives should differ from positives
        overlap = set(negs) & set(positives)
        assert len(overlap) / len(negs) < 0.1

    def test_train_classifier_metrics(self, esm2):
        tokenizer, model = esm2
        # Small synthetic dataset
        pos_seqs = SAMPLE_SEQUENCES * 5
        neg_seqs = generate_negative_sequences(pos_seqs, n_negatives=20, seed=99)

        pos_embs = generate_embeddings(pos_seqs, tokenizer, model)
        neg_embs = generate_embeddings(neg_seqs, tokenizer, model)

        X = np.vstack([pos_embs, neg_embs])
        y = np.concatenate([np.ones(len(pos_seqs)), np.zeros(len(neg_seqs))])

        clf, metrics = train_classifier(X, y, test_size=0.3)

        assert metrics["auc_roc"] > 0.5
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1"] <= 1
        assert clf is not None


# ── Generator Tests ───────────────────────────────────────────────

class TestGenerator:
    def test_mutate_sequence_length_preserved(self):
        seq = "ACDEFGHIKL"
        mutated = mutate_sequence(seq, n_mutations=2, rng=random.Random(42))
        assert len(mutated) == len(seq)

    def test_mutate_sequence_differs(self):
        seq = "ACDEFGHIKL"
        mutated = mutate_sequence(seq, n_mutations=3, rng=random.Random(42))
        assert mutated != seq

    def test_mutate_sequence_valid_aas(self):
        seq = "ACDEFGHIKLMNPQRSTVWY"
        mutated = mutate_sequence(seq, n_mutations=5, rng=random.Random(42))
        assert all(c in VALID_AAS for c in mutated)

    def test_generate_mutations_count(self):
        seeds = ["ACDEFGHIKLMNPQ", "STVWYACDEFGHIK"]
        variants = generate_mutations(seeds, n_variants_per_seed=10)
        assert len(variants) > 0
        # Should not contain originals
        for seed in seeds:
            assert seed not in variants

    def test_generate_mutations_valid(self):
        seeds = ["ACDEFGHIKLMNPQ", "STVWYACDEFGHIK"]
        variants = generate_mutations(seeds, n_variants_per_seed=10)
        for v in variants:
            assert all(c in VALID_AAS for c in v)
            assert MIN_LENGTH <= len(v) <= MAX_LENGTH

    def test_score_candidates(self, esm2):
        tokenizer, model = esm2

        # Train a quick classifier
        pos_seqs = SAMPLE_SEQUENCES * 5
        neg_seqs = generate_negative_sequences(pos_seqs, n_negatives=20, seed=99)
        pos_embs = generate_embeddings(pos_seqs, tokenizer, model)
        neg_embs = generate_embeddings(neg_seqs, tokenizer, model)
        X = np.vstack([pos_embs, neg_embs])
        y = np.concatenate([np.ones(len(pos_seqs)), np.zeros(len(neg_seqs))])
        clf, _ = train_classifier(X, y)

        # Score some candidates
        candidates = ["GIGKFLHSAKKFGKAFVGEIMNS", "ACDEFGHIKLMNPQRSTVWY"]
        results = score_candidates(candidates, clf, tokenizer, model, threshold=0.0)

        assert isinstance(results, pd.DataFrame)
        assert "sequence" in results.columns
        assert "amp_probability" in results.columns
        assert len(results) > 0
        assert all(0 <= p <= 1 for p in results["amp_probability"])
