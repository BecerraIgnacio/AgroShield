#!/bin/bash
# AgroShield Overnight Training — single command, go to sleep
#
# Usage:  ./run_overnight.sh
#   or:   bash run_overnight.sh
#
# Runs on A40 GPU. Logs to train_overnight.log.
# Estimated runtime: 4-8 hours.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo " AgroShield Overnight Training"
echo "=========================================="
echo "Start: $(date)"
echo "Dir:   $SCRIPT_DIR"
echo ""

# Activate venv if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "Activating .venv..."
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    echo "Activating venv..."
    source venv/bin/activate
fi

# Check Python
echo "Python: $(python3 --version 2>&1)"

# Check GPU
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name() if torch.cuda.is_available() else \"none\"}')" 2>/dev/null || echo "Warning: torch not found or no GPU"

# Install any missing deps (won't break existing ones)
echo ""
echo "Checking dependencies..."
pip install --quiet --upgrade transformers torch scikit-learn biopython modlamp pandas numpy scipy 2>/dev/null || true

# Run the training
echo ""
echo "Starting training pipeline..."
echo "Logging to: $SCRIPT_DIR/train_overnight.log"
echo "You can monitor with: tail -f $SCRIPT_DIR/train_overnight.log"
echo ""

python3 train_overnight.py 2>&1 | tee -a train_overnight_stdout.log

EXIT_CODE=$?
echo ""
echo "=========================================="
echo " Training finished at $(date)"
echo " Exit code: $EXIT_CODE"
echo " Check train_overnight.log for details"
echo "=========================================="
