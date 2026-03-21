# Phase 5: Validation & Metrics

## Goal
Produce quantitative evidence that the pipeline works. This is what convinces the judges.

## Deliverables
1. `scripts/validate.py` — Run all validation experiments
2. `scripts/plots.py` — Generate publication-quality figures
3. `results/` — Output figures and metrics JSON

## Validation Experiments

### 1. Classifier Performance
- AUC-ROC curve on held-out test set
- Precision-Recall curve
- Confusion matrix
- Target: AUC > 0.85

### 2. Known AMP Recovery
- Take 50 known effective AMPs, remove from training set
- Run pipeline, check how many are recovered in top-N results
- Report recovery rate at N=20, N=50, N=100
- Target: >60% recovery at N=50

### 3. Property Distribution Analysis
- Compare generated peptides vs natural AMPs:
  - Length distribution
  - Net charge distribution
  - Hydrophobicity (GRAVY score)
  - Isoelectric point
- Use KS-test for statistical comparison
- Generated should overlap with natural distributions

### 4. Negative Control
- Generate random peptides (same length distribution)
- Score with pipeline
- Generated AMPs should score significantly higher than random
- Report p-value from Mann-Whitney U test

### 5. Diversity Analysis
- Pairwise sequence identity of top-20 candidates
- Should show diversity (avg identity < 70%)
- Ensures we're not just generating near-duplicates

## Output
- `results/metrics.json` — All numerical results
- `results/roc_curve.png`
- `results/property_distributions.png`
- `results/recovery_rate.png`
- `results/random_vs_generated.png`

## Constraints
- All plots: matplotlib/plotly, white background, labeled axes
- Figures must be presentation-ready (hackathon pitch)
- Include statistical tests (p-values) where applicable
