# Phase 2: ML Model — AMP Classifier + Peptide Generator

## Goal
Train a binary classifier (AMP vs non-AMP) and build a peptide generation pipeline using ESM-2 embeddings.

## Deliverables
1. `scripts/embeddings.py` — Generate ESM-2 embeddings for all sequences
2. `scripts/train_classifier.py` — Train AMP/non-AMP classifier
3. `scripts/generate_peptides.py` — Novel peptide generation via guided perturbation
4. `models/` — Saved model artifacts
5. `test_model.py` — Tests for classifier and generator

## Architecture

### Embeddings (ESM-2)
- Model: `facebook/esm2_t6_8M_UR50D` (smallest, fast on CPU)
- Extract per-sequence embedding (mean pooling over residues)
- Cache embeddings to `models/embeddings_cache.npz`

### Classifier
- Input: ESM-2 embedding (320-dim)
- Model: sklearn RandomForest or XGBoost
- Negatives: random peptides from UniRef + shuffled AMP sequences
- Split: 80/20 stratified
- Metrics: AUC-ROC, precision, recall, F1
- Save: joblib dump to `models/amp_classifier.joblib`

### Peptide Generator
Strategy — mutation-based generation:
1. Take top-scoring known AMPs against target pathogen
2. Apply single/double point mutations at non-conserved positions
3. Score variants with classifier
4. Keep variants that score above threshold (>0.7 probability)
5. Filter for physicochemical viability (see Phase 3)

Alternative strategy — embedding interpolation:
1. Interpolate between embeddings of effective AMPs
2. Find nearest real sequences to interpolated embeddings
3. Use as generation seeds

## Constraints
- Must work on CPU (no GPU assumed for hackathon)
- Embedding generation should batch sequences (batch_size=32)
- Generator must produce ≥50 novel candidates per pathogen query
- All generated sequences: length 10-50 AA, standard amino acids only
