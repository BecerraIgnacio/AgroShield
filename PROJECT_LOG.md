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
