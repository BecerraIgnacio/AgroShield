# AgroShield

AgroShield is an AI-guided antimicrobial peptide discovery platform for crop protection.

The product combines protein language models, sequence generation, diversity filtering, and multi-objective ranking to move from biological priors to a small peptide shortlist that can enter experimental validation and scale-up workflows.

## What AgroShield Does

- Targets agricultural pathogens such as *Fusarium*, *Xanthomonas*, *Pseudomonas*, *Botrytis*, and related crop threats
- Uses curated antimicrobial peptide references to anchor model training
- Explores peptide sequence space with an ESM-2-based discovery pipeline
- Ranks candidates across antimicrobial activity, hemolysis risk, phytotoxicity, stability, and synthesizability
- Frames discovery as a path to production, not just a scoring exercise

## Current Public Snapshot

This repository contains:

- The public-facing AgroShield website in [`04_app/site`](./04_app/site)
- The lightweight static server in [`04_app/server.js`](./04_app/server.js)
- The end-to-end overnight training pipeline in [`train_overnight.py`](./train_overnight.py)
- Supporting data-ingestion, modeling, and scoring scripts in [`01_data`](./01_data), [`02_model`](./02_model), and [`03_scoring`](./03_scoring)

This public repo intentionally does **not** include:

- Generated candidate libraries
- Ranked output CSVs
- Model checkpoints and binary artifacts
- Raw database dumps
- Internal notes, logs, and scratch files

That boundary is deliberate. AgroShield is built to commercialize peptide discovery, not to publish the full candidate inventory.

## Repository Structure

```text
.
├── 01_data/              # Data ingestion and preprocessing scripts
├── 02_model/             # Embedding, training, and generation scripts
├── 03_scoring/           # Multi-objective scoring logic
├── 04_app/               # Website and earlier app components
│   ├── site/             # Current public website
│   └── server.js         # Static file server
├── run_overnight.sh      # Convenience launcher for the full pipeline
└── train_overnight.py    # Intensive overnight pipeline
```

## Website Quick Start

Requirements:

- Node.js 18+

Run:

```bash
cd 04_app
npm install
npm start
```

Then open:

```text
http://127.0.0.1:4173
```

If port `4173` is already in use:

```bash
PORT=4174 npm start
```

## Pipeline Overview

The intensive pipeline in `train_overnight.py` is designed around six phases:

1. Acquire AMP and negative training data
2. Fine-tune an ESM-2 3B classifier
3. Run multi-round evolutionary candidate generation
4. Filter for diversity in embedding space
5. Score candidates across multiple biological and manufacturability criteria
6. Summarize outputs for validation planning

The ranking stack is designed to prioritize candidates that are not only active, but also more realistic to validate and scale.

## Experimental Direction

AgroShield is designed around a downstream path to expression and scale-up:

- fusion expression with MBP-style solubility support
- inducible production to reduce toxicity during growth
- secretion-first recovery strategies
- purification, cleavage, and final peptide isolation
- bioreactor-oriented process planning

## Positioning

AgroShield is built for:

- crop protection companies
- agri-biotech labs
- research and commercialization partners working on next-generation agricultural bioactives

## Status

This is an active hackathon-to-startup project. The current repository snapshot focuses on the product story, the platform architecture, and the core discovery pipeline.
