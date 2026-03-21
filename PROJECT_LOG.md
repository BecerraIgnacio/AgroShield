# AgroShield — Project Log & Explainer

## What is AgroShield?

AgroShield is an AI pipeline that **designs new antimicrobial peptides (AMPs) to protect crops from diseases**, replacing toxic chemical pesticides.

---

## Key Concepts (Plain English)

### What are Antimicrobial Peptides (AMPs)?
- Short chains of **amino acids** (the building blocks of proteins), typically 10–50 units long
- They exist in nature — plants, animals, and insects produce them to fight infections
- AMPs kill bacteria and fungi by **punching holes in their cell membranes**
- Unlike chemical pesticides, pathogens have a hard time developing resistance to AMPs
- They're biodegradable and non-toxic to humans

### What is ESM-2?
- A **protein language model** made by Meta/Facebook (like ChatGPT but for proteins)
- Trained on ~250 million protein sequences from nature
- It reads an amino acid sequence (e.g., `GIGKFLHSAKKFGK`) and outputs an **embedding** — a numerical fingerprint (a vector of 2560 numbers) that captures the protein's properties
- Similar proteins get similar fingerprints, so we can use math to compare and classify them
- We're using the **3B parameter version** (3 billion parameters), run on an A40 GPU with 48GB VRAM

### What is an Embedding?
- Think of it as converting a word (the peptide sequence) into a point in a high-dimensional space
- Peptides that do similar things end up near each other in this space
- This lets us use machine learning on protein sequences (ML needs numbers, not letters)

---

## What We Built — Phase by Phase

### Phase 01: Data Collection (`01_data/`)
**What we did:** Gathered known AMPs from scientific databases.

- Scraped **DRAMP** (a public database of antimicrobial peptides)
- Collected **530 unique AMP sequences** with metadata:
  - What organism they target (e.g., *Fusarium oxysporum*, a fungus that kills tomatoes)
  - Their **MIC** (Minimum Inhibitory Concentration) — how little peptide you need to kill the pathogen (lower = more potent)
  - Their activity type (antibacterial, antifungal, etc.)
- Built a **pathogen-crop mapping**: which pathogens attack which crops
  - Example: *Fusarium oxysporum* → tomato, banana, cotton
  - Example: *Xanthomonas oryzae* → rice

### Phase 02: ML Model (`02_model/`)
**What we did:** Built an AI pipeline with three stages.

#### Stage 1 — Embeddings (`scripts/embeddings.py`)
- Fed all 530 AMP sequences into **ESM-2 (3B model)**
- Got back a **2560-dimensional vector** for each sequence
- These vectors encode the biological properties of each peptide
- Cached results to avoid re-running (expensive GPU computation)

#### Stage 2 — Classifier (`scripts/train_classifier.py`)
- **Goal:** Train a model that can tell "is this sequence an AMP or not?"
- **Positive examples:** Our 530 real AMPs (label = 1)
- **Negative examples:** We generated fake non-AMPs two ways:
  - Took real AMPs and **shuffled their letters** (destroys the biological structure)
  - Generated **random amino acid strings** of similar lengths
- Embedded all negatives with ESM-2 too
- Trained a **Random Forest classifier** (200 decision trees) on the embeddings
- Metrics: AUC-ROC, precision, recall, F1 — measures how well it distinguishes real AMPs from random peptides

#### Stage 3 — Generator (`scripts/generate_peptides.py`)
- **Goal:** Create **new, never-before-seen peptides** that the classifier thinks are real AMPs
- Two generation strategies:
  1. **Mutation-based:** Take the best known AMPs against a target pathogen, randomly swap 1–3 amino acids, keep variants that still score high
  2. **Interpolation-based:** Blend the embeddings of two good AMPs (like mixing colors), find the closest real sequence to the blend, then mutate that
- Score all candidates with the classifier → keep those with >70% AMP probability
- Output: a ranked list of novel peptide candidates

---

## Infrastructure

| Component | Detail |
|-----------|--------|
| Local dev | Arch Linux, CPU-only PyTorch, ESM-2 8M model for testing |
| GPU compute | RunPod A40 (48GB VRAM), 150GB disk |
| ESM-2 model | `facebook/esm2_t36_3B_UR50D` — 3 billion parameters, fp16 precision |
| Classifier | scikit-learn RandomForest, saved as `.joblib` |
| Code | Python 3.11, pushed to GitHub: `BecerraIgnacio/agroshield` |

---

## Pipeline Execution Order

```
1. python -m 02_model.scripts.embeddings        # ~15-30 min on A40
   → Produces: models/embeddings_cache.npz

2. python -m 02_model.scripts.train_classifier   # ~5 min
   → Produces: models/amp_classifier.joblib

3. python -m 02_model.scripts.generate_peptides   # ~10 min
   → Produces: models/generated_candidates.csv
```

### Phase 03: Multi-Score Ranking (`03_scoring/`)
**What we did:** Scored all 81 generated peptide candidates across 5 dimensions to find the best ones.

#### The 5 Scoring Dimensions

1. **Antimicrobial Activity (weight: 35%)** — The classifier's probability that the peptide is a real AMP. Higher = more likely to kill pathogens. Our candidates range from 0.65 to 0.79.

2. **Hemolytic Toxicity (weight: 25%)** — Will the peptide destroy human red blood cells? Predicted from hydrophobic moment, hydrophobicity, and charge. Lower is safer. We reject anything above 0.5. Result: **56/81 candidates are safe** (score < 0.5).

3. **Phytotoxicity (weight: 15%)** — Will the peptide harm the plant it's supposed to protect? Based on length, charge, and hydrophobicity. Plant-safe peptides are short (<30 AA), moderately cationic (+2 to +6), and not too hydrophobic. Result: **all 81 candidates are plant-safe** (all below 0.5).

4. **Stability (weight: 15%)** — Will the peptide survive in the environment long enough to work? Uses the **instability index** (BioPython): peptides with index < 40 are considered stable. Normalized to 0–1. Result: **54/81 are stable** (score > 0.5).

5. **Synthesizability (weight: 10%)** — Can we actually manufacture this peptide? Penalizes: length > 30 AA, many cysteines (disulfide bond complexity), consecutive prolines, rare amino acids. Result: most candidates score high — they're makeable.

#### Combined Score Formula
```python
combined = (0.35 × activity) + (0.25 × (1 − hemolytic)) +
           (0.15 × (1 − phytotoxicity)) + (0.15 × stability) +
           (0.10 × synthesizability)
```

#### Results Summary

| Metric | Value |
|--------|-------|
| Total candidates scored | 81 |
| Combined score > 0.70 (strong) | 23 |
| Combined score > 0.60 (viable) | 76 |
| Hemolytic-safe (< 0.5) | 56/81 |
| Plant-safe (< 0.5) | 81/81 |
| Stable (> 0.5) | 54/81 |

#### Top 5 Candidates

| Rank | ID | Sequence | Length | Combined | Activity | Hemolytic | Stability |
|------|----|----------|--------|----------|----------|-----------|-----------|
| 1 | GEN_0056 | RLCRIVVIRTCR | 12 | 0.78 | 0.67 | 0.39 | 0.97 |
| 2 | GEN_0051 | KGLKFCGEQVWQVYLLKT | 18 | 0.78 | 0.68 | 0.44 | 1.00 |
| 3 | GEN_0039 | KGLKFVGSEVWQVYLLKT | 18 | 0.76 | 0.69 | 0.47 | 1.00 |
| 4 | GEN_0003 | LIQDCRGVRASGAQLAKIKLIGCLQF | 26 | 0.75 | 0.77 | 0.50 | 0.78 |
| 5 | GEN_0004 | KGLKFGGSPVWQVYLLKT | 18 | 0.75 | 0.77 | 0.45 | 0.64 |

**Best overall candidate: GEN_0056** — a short 12-AA peptide that's very stable, low-toxicity, easy to synthesize, and has moderate antimicrobial activity. In a real pipeline, these top 20 would go to wet-lab MIC assays to confirm actual pathogen-killing ability.

#### Pipeline Execution
```
4. python -m 03_scoring.scripts.scoring              # ~10 sec
   → Produces: output/scored_all.csv, output/top_candidates.csv
```

---

## Why This Matters

- Chemical pesticides contaminate soil, water, and food
- Pathogen resistance to pesticides is growing
- AMPs are a **biological alternative**: targeted, biodegradable, hard to develop resistance against
- By using AI to design new AMPs, we can rapidly generate candidates tailored to specific crop diseases
- This approach is faster and cheaper than traditional wet-lab peptide discovery

---

## Glossary

| Term | Meaning |
|------|---------|
| AMP | Antimicrobial Peptide — a short protein that kills microbes |
| Amino acid | Building block of proteins, 20 types (A, C, D, E, F, G, H, I, K, L, M, N, P, Q, R, S, T, V, W, Y) |
| Embedding | Numerical representation of a sequence (vector of numbers) |
| ESM-2 | Evolutionary Scale Modeling — Meta's protein language model |
| MIC | Minimum Inhibitory Concentration — lowest dose that stops pathogen growth |
| Random Forest | ML algorithm that uses many decision trees voting together |
| fp16 | Half-precision floating point — uses less GPU memory |
| VRAM | Video RAM — GPU memory |
| Pathogen | Organism that causes disease (bacteria, fungi, viruses) |
| Hemolytic | Destroying red blood cells — a toxic side effect to avoid |
| Phytotoxicity | Toxicity to plants — the peptide must not harm the crop it protects |
| Instability index | Measure of protein stability in a test tube; < 40 = stable |
| Hydrophobic moment | How unevenly hydrophobic residues are distributed on a helix — relates to membrane interaction |
| Synthesizability | How easy/cheap it is to manufacture the peptide in a lab |
