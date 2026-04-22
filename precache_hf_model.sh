#!/bin/bash
# Run ONCE on the gwendolen login node before the first `sbatch job.sh`.
# Downloads the SentenceTransformer embedding model into the shared /data
# HF cache so compute nodes can load it offline via HF_HUB_OFFLINE=1.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON_MODULE="${PYTHON_MODULE:-Python/3.11.11}"
HF_CACHE_ROOT="${HF_CACHE_ROOT:-/data/user/ext-nobile_a/hf_cache}"
MODEL_NAME="${MODEL_NAME:-BAAI/bge-code-v1}"

module load "$PYTHON_MODULE"

cd "$SCRIPT_DIR"
source .venv/bin/activate

mkdir -p "$HF_CACHE_ROOT"
export HF_HOME="$HF_CACHE_ROOT"
export HUGGINGFACE_HUB_CACHE="$HF_CACHE_ROOT/hub"
export TRANSFORMERS_CACHE="$HF_CACHE_ROOT/transformers"
export MODEL_NAME

echo "Pre-caching $MODEL_NAME into $HF_CACHE_ROOT ..."
echo "(If you hit HF rate limits, 'export HF_TOKEN=<your-token>' before re-running.)"

python - <<'PY'
import os
from sentence_transformers import SentenceTransformer

model_name = os.environ["MODEL_NAME"]
SentenceTransformer(model_name, trust_remote_code=True)
print(f"Model '{model_name}' cached under {os.environ['HF_HOME']}.")
PY
