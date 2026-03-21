# Phase 3: Multi-Score Ranking Filter

## Goal
Score and rank peptide candidates across multiple dimensions to select the most promising ones.

## Deliverables
1. `scripts/scoring.py` — Main scoring pipeline
2. `scripts/properties.py` — Physicochemical property calculator
3. `scripts/toxicity.py` — Toxicity prediction module
4. `test_scoring.py` — Tests for scoring functions

## Scoring Dimensions

### 1. Antimicrobial Activity Score (0-1)
- From Phase 2 classifier probability
- Higher = more likely to be antimicrobial

### 2. Hemolytic Toxicity Score (0-1, lower is better)
- Use modlAMP or manual feature-based prediction
- Features: hydrophobic moment, net charge, % hydrophobic residues
- Threshold: reject if score > 0.5

### 3. Phytotoxicity Prediction (0-1, lower is better)
- Heuristic based on: cationicity, amphipathicity, length
- Plant-safe peptides tend to be: shorter (<30 AA), moderately cationic (+2 to +6), low hydrophobicity

### 4. Stability Score (0-1)
- Instability index (BioPython ProteinAnalysis)
- Peptides with instability index < 40 are considered stable
- Normalize to 0-1 scale

### 5. Synthesizability Score (0-1)
- Based on: sequence length (shorter = easier), amino acid complexity, absence of rare AAs (Cys-Cys bridges)
- Penalty for: length > 30, >2 cysteines, consecutive prolines

## Combined Score
```python
combined = (0.35 * activity + 0.25 * (1 - hemolytic) +
            0.15 * (1 - phytotoxicity) + 0.15 * stability +
            0.10 * synthesizability)
```

## Output Format
DataFrame with columns: id, sequence, length, charge, activity_score, hemolytic_score, phytotoxicity_score, stability_score, synthesizability_score, combined_score, rank
Sorted by combined_score descending. Top 20 candidates returned.

## Constraints
- All scores normalized to [0, 1]
- Use BioPython.SeqUtils.ProtParam for molecular properties
- modlAMP for helical wheel and amphipathicity calculations
- No external API calls — all scoring runs locally
