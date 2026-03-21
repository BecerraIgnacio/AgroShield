# Phase 4: Streamlit Frontend

## Goal
Interactive web demo for the hackathon pitch. User picks pathogen → sees ranked AMP candidates with visualizations.

## Deliverables
1. `app.py` — Main Streamlit application
2. `components/viz.py` — Visualization functions (radar chart, property plots)
3. `components/structure.py` — 3D structure viewer (py3Dmol/stmol)
4. `components/pipeline.py` — Pipeline orchestration (calls phases 1-3)
5. `assets/logo.png` — Project logo (optional)

## UI Layout

### Sidebar
- Project title + description
- Pathogen selector (dropdown from pathogen_crop_map.json)
- Show affected crops when pathogen selected
- "Generate Candidates" button
- Number of candidates slider (10-50, default 20)

### Main Area
Tab 1 — **Results Table**
- Ranked candidates with all scores
- Color-coded cells (green=good, red=bad)
- Download CSV button

Tab 2 — **Analysis**
- Radar chart: 5 scoring dimensions for top 5 candidates
- Property distribution plots (charge, length, hydrophobicity)
- Comparison: generated vs known AMPs

Tab 3 — **3D Structure**
- Peptide selector from top candidates
- 3D structure via ESMFold API or py3Dmol helix prediction
- Sequence annotation (colored by property)

Tab 4 — **About**
- Problem description
- Pipeline explanation
- Team info

## Visual Style
- Clean, professional, dark sidebar
- Color palette: greens and earth tones (agriculture theme)
- Use st.metric() for key stats
- Use st.columns() for layout

## Constraints
- Must load fast — precompute what possible, cache with @st.cache_data
- Handle ESMFold API timeout gracefully (show helix prediction as fallback)
- Works without GPU
- Responsive enough for live demo (< 30s pipeline run with cached embeddings)
