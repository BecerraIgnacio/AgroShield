# AgroShield — Execution Plan

## 1. Execute `01_data` — Pathogen DB + AMP Retrieval Pipeline
Build pathogen-crop mapping and AMP sequence retrieval from public databases (DRAMP/APD3/dbAMP). Output: curated dataset of AMPs with target pathogen annotations.

## 2. Execute `02_model` — AMP Classifier + Peptide Generator
ESM-2 embeddings → train binary AMP classifier → implement sequence perturbation generator for novel candidates. Output: trained model + generation function.

## 3. Execute `03_scoring` — Multi-Score Ranking Filter
Score peptide candidates on: predicted antimicrobial activity, hemolytic toxicity, phytotoxicity, stability, synthesizability. Output: ranked candidates dataframe.

## 4. Execute `04_app` — Streamlit Demo App
Interactive frontend: pathogen selector → pipeline trigger → results table + radar charts + 3D structure viewer. Output: working demo.

## 5. Execute `05_validation` — Metrics & Benchmarks
AUC-ROC on held-out set, known AMP recovery rate, property distribution comparison vs natural AMPs, negative control vs random peptides. Output: validation report with figures.
