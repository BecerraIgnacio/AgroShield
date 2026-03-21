# AgroShield — AI-Powered Antimicrobial Peptide Design for Crop Protection

## Project Overview
Bioinformatics pipeline that designs novel antimicrobial peptides (AMPs) to replace chemical pesticides in agriculture. User selects a crop pathogen → system retrieves known AMPs → generates novel candidates via ESM-2 → scores for activity/toxicity/stability → outputs ranked results with 3D structures.

## Architecture
```
01_data/    → Pathogen-crop DB + AMP retrieval from DRAMP/APD3/dbAMP
02_model/   → ESM-2 embeddings + AMP classifier + peptide generator
03_scoring/ → Multi-score filter (activity, toxicity, stability, synthesizability)
04_app/     → Streamlit frontend (interactive demo)
05_validation/ → Metrics: AUC-ROC, known AMP recovery, property distributions
```

Each folder is an independent module with its own CLAUDE.md. **Work in one folder at a time** to minimize context. Read the folder's CLAUDE.md before starting work there.

## Tech Stack
- Python 3.11+, pip with requirements.txt per folder
- Core: BioPython, pandas, numpy, scikit-learn, torch
- Protein: ESM-2 (facebook/esm2_t6_8M_UR50D for speed), modlAMP
- Frontend: Streamlit
- Viz: plotly, matplotlib, py3Dmol
- No database — flat files (CSV/JSON/FASTA)

## Conventions
- Type hints on all functions
- One module = one responsibility
- Functions over classes unless state is needed
- f-strings, pathlib for paths
- pytest for tests, files named test_*.py inside each folder
- Print nothing to stdout in library code — return data structures
- Constants in UPPERCASE at module top
- Requirements: each folder has its own requirements.txt; root has requirements.txt that combines all

## RTK
Use `rtk` prefix for all shell commands that produce verbose output (git, ls, grep, test runs).

## Subagents
Agents are in `.claude/agents/`. Use them for:
- `python-pro`: Core Python coding tasks
- `data-scientist`: ML model design, EDA, feature engineering
- `code-reviewer`: Review before finalizing each phase
- `test-automator`: Generate and run test suites
- `scientific-researcher`: Look up AMP databases, papers, protein methods

## Workflow Per Phase
1. Read the phase's CLAUDE.md
2. Implement core logic
3. Write tests
4. Run code-reviewer agent
5. Move to next phase

## Do NOT
- Over-engineer or add unnecessary abstractions
- Add docstrings to obvious functions
- Create ORM models — use dicts/dataframes
- Install heavy deps when lighter ones work
- Add logging framework — use print() for debug, remove before commit
