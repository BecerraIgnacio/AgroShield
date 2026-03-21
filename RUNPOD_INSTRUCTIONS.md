# RunPod Overnight Training — Instructions

## What's Running
Overnight training pipeline on A40 GPU:
1. Expand dataset 530 → 3000 AMPs
2. ESM-2 3B embeddings (2560-dim)
3. Fine-tune ESM-2 650M classifier (20 epochs)
4. Evolutionary AMP generation (50 gens, 500+ candidates)
5. Multi-dimensional scoring
6. Embed final candidates

## When You Wake Up

### 1. SSH into RunPod and check results
```bash
tail -100 /agroshield/train_overnight.log
```

### 2. If it finished successfully
Results are in:
- `02_model/models/esm2_amp_classifier.pt` — fine-tuned classifier
- `02_model/models/generated_candidates.csv` — new candidates (overwrites old)
- `02_model/models/generated_candidates_v2.csv` — same, backup copy
- `03_scoring/output/scored_all.csv` — scored results (overwrites old)
- `03_scoring/output/top_candidates.csv` — top 20
- `01_data/data/processed/amps_unified_expanded.csv` — expanded dataset
- `02_model/models/embeddings_cache_3B.npz` — full 2560-dim embeddings
- `02_model/models/checkpoints/best_classifier.pt` — best checkpoint

### 3. Copy results back
Option A — push from RunPod:
```bash
cd /agroshield
git add -A
git commit -m "Add overnight training results from A40"
git push origin master
```

Option B — download files with scp (if git push fails):
```bash
# From your local machine:
scp -r root@<RUNPOD_IP>:/agroshield/02_model/models/ agroshield/02_model/
scp -r root@<RUNPOD_IP>:/agroshield/03_scoring/output/ agroshield/03_scoring/
scp root@<RUNPOD_IP>:/agroshield/train_overnight.log agroshield/
scp root@<RUNPOD_IP>:/agroshield/01_data/data/processed/amps_unified_expanded.csv agroshield/01_data/data/processed/
```

### 4. If it crashed
Check the log for the error:
```bash
cat /agroshield/train_overnight.log
cat /agroshield/train_overnight_stdout.log
```

Each phase has error recovery — if phase 2 fails, it continues with old embeddings, etc.
Only phase 3 (classifier) is critical — if that fails, the script exits.

To re-run:
```bash
cd /agroshield
rm -f train_overnight.log train_overnight_stdout.log
nohup bash run_overnight.sh > /dev/null 2>&1 &
```

### 5. Update the Streamlit app
The overnight script overwrites the original files, so the app should pick up new results automatically. Just run:
```bash
streamlit run 04_app/app.py
```

## Key Files Created by This Run
| File | Description |
|------|-------------|
| `train_overnight.log` | Full training log with metrics |
| `esm2_amp_classifier.pt` | Fine-tuned ESM-2 650M model |
| `embeddings_cache_3B.npz` | 3000 × 2560 embeddings |
| `generated_candidates_v2.csv` | 500+ evolved candidates |
| `scored_all_v2.csv` | All candidates scored |
| `top_candidates_v2.csv` | Top 20 ranked |
