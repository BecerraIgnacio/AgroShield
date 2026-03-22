#!/bin/bash
# Setup script for RunPod A40 instance
set -e

echo "=== AgroShield Phase 02 — Pod Setup ==="

# Install system deps
apt-get update -qq && apt-get install -y -qq git python3-venv python3-pip > /dev/null 2>&1
echo "✓ System deps"

# Clone or copy project (adjust URL to your repo)
# git clone <YOUR_REPO_URL> /workspace/agroshield
# cd /workspace/agroshield

# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install PyTorch with CUDA
pip install -q torch --index-url https://download.pytorch.org/whl/cu124

# Install project deps
pip install -q transformers scikit-learn joblib xgboost biopython pandas numpy

echo "✓ Python deps"

# Verify GPU
python3 -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)} | VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')"

echo ""
echo "=== Ready. Run the pipeline: ==="
echo "  source .venv/bin/activate"
echo "  python -m 02_model.scripts.embeddings"
echo "  python -m 02_model.scripts.train_classifier"
echo "  python -m 02_model.scripts.generate_peptides"
