# Phase 1: Data Pipeline — Pathogen DB + AMP Retrieval

## Goal
Build a curated dataset of antimicrobial peptides mapped to agricultural pathogens.

## Data Sources
- **DRAMP** (http://dramp.cpu-bioinfor.org/): Download general AMPs dataset CSV
- **APD3** (https://aps.unmc.edu/): Antimicrobial Peptide Database, downloadable
- **dbAMP** (https://yvq.github.io/dbAMP/): Integrated AMP database
- Fallback: use UniProt with keyword "antimicrobial peptide" filtered to plant pathogens

## Deliverables
1. `scripts/fetch_amps.py` — Download and parse AMP databases into unified format
2. `scripts/build_pathogen_db.py` — Curated pathogen-crop mapping (JSON)
3. `scripts/preprocess.py` — Clean, deduplicate, standardize sequences
4. `data/processed/amps_unified.csv` — Columns: id, sequence, source_db, target_organism, activity_type, MIC_value
5. `data/processed/pathogen_crop_map.json` — {pathogen: {crops: [], kingdom: "fungi"|"bacteria", description: ""}}
6. `test_data.py` — Tests for data integrity

## Pathogen-Crop Map (minimum viable)
Include at least these high-impact pathogens:
- Fusarium oxysporum (tomato, banana wilt)
- Xanthomonas campestris (citrus canker, brassica black rot)
- Botrytis cinerea (grey mold — grapes, strawberries)
- Pseudomonas syringae (bacterial speck — tomato, beans)
- Magnaporthe oryzae (rice blast)
- Puccinia graminis (wheat stem rust)
- Ralstonia solanacearum (bacterial wilt — potato, tomato)

## Schema
```python
# AMP record
{"id": str, "sequence": str, "length": int, "source_db": str,
 "target_organisms": list[str], "activity": str, "mic_um": float | None}

# Pathogen record
{"name": str, "kingdom": str, "crops": list[str],
 "economic_impact": str, "description": str}
```

## Constraints
- No API keys required — use publicly downloadable files
- If a DB is unreachable, generate synthetic reference data from known AMP sequences in literature
- Minimum 500 AMP sequences in final dataset
- All sequences must be valid amino acid strings (20 standard AAs)
