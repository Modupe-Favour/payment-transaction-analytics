#!/usr/bin/env bash
# ============================================================
# Payment Transaction Analytics — one-shot bootstrap script
# ============================================================
# Generates the synthetic data, loads it into the database,
# and launches the Streamlit dashboard.
#
# Usage:
#   ./setup_and_run.sh           # full pipeline
#   ./setup_and_run.sh --skip-gen # skip data generation (use existing)
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

SKIP_GEN=false
if [[ "${1:-}" == "--skip-gen" ]]; then
  SKIP_GEN=true
fi

PYTHON="${PYTHON:-python3}"

echo "============================================================"
echo "  Payment Transaction Analytics — bootstrap"
echo "============================================================"
echo ""

# 1. Check Python deps
echo "[1/4] Checking Python dependencies..."
$PYTHON -c "import pandas, numpy, sqlalchemy, streamlit, plotly" 2>/dev/null || {
  echo "  Missing dependencies. Installing from requirements.txt..."
  $PYTHON -m pip install -r requirements.txt
}

# 2. Generate data
if [[ "$SKIP_GEN" == "true" ]]; then
  echo "[2/4] Skipping data generation (--skip-gen)"
else
  echo "[2/4] Generating 1.2M synthetic transactions (~12 seconds)..."
  $PYTHON data/generate_transactions.py --rows 1200000
fi
echo ""

# 3. Load into database
echo "[3/4] Loading parquet into database..."
$PYTHON -m src.database load
echo ""

# 4. Launch dashboard
echo "[4/4] Launching Streamlit dashboard..."
echo "  → http://localhost:8501"
echo "  (Press Ctrl+C to stop)"
echo ""
$PYTHON -m streamlit run streamlit_app.py --server.headless true
