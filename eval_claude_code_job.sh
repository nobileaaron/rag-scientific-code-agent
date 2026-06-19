#!/bin/bash
#SBATCH --job-name=rag-ippl-cc-eval
#SBATCH --error=gwendolen_cc_eval.error
#SBATCH --output=gwendolen_cc_eval.out
#SBATCH --time=0
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --clusters=gmerlin6
#SBATCH --partition=gwendolen
#SBATCH --account=gwendolen
#SBATCH --gpus=1
#
# SLURM wrapper for the Claude Code model-matrix eval (NOT the RAG-pipeline
# eval in eval_job.sh). It sets up the environment the way job.sh does, then
# hands off to run_eval_ssh.sh, which starts Ollama + the LiteLLM proxy and
# drives Claude Code over each local model.
#
# Output: docs/evaluations/answers/claude_code_<label>_<timestamp>.json
# Docs:   docs/evaluations/CLAUDE_CODE_EVAL.md
#
# Submit with:        sbatch eval_claude_code_job.sh
# Subset of models:   EVAL_MODELS="qwen25_7b_q4km gemma4_12b" sbatch eval_claude_code_job.sh
# Longer timeouts:    PER_QUESTION_TIMEOUT=2400 sbatch eval_claude_code_job.sh

set -euo pipefail

ulimit -c unlimited

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(pwd)}"

# Mirror the environment setup from job.sh — adjust if your cluster changes.
PYTHON_MODULE="${PYTHON_MODULE:-Python/3.11.11}"
OLLAMA_HOME="${OLLAMA_HOME:-/data/user/ext-nobile_a/ollama}"
HF_CACHE_ROOT="${HF_CACHE_ROOT:-/data/user/ext-nobile_a/hf_cache}"

module load "$PYTHON_MODULE"

export PATH="$OLLAMA_HOME/bin:$PATH"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$OLLAMA_HOME/models}"

mkdir -p "$HF_CACHE_ROOT/hub"
export HF_HOME="$HF_CACHE_ROOT"
export HUGGINGFACE_HUB_CACHE="$HF_CACHE_ROOT/hub"
unset TRANSFORMERS_CACHE

cd "$SCRIPT_DIR"
source .venv/bin/activate

# The claude CLI must be reachable. If it lives outside the venv/standard PATH,
# export CLAUDE_BIN_DIR before sbatch and we prepend it here.
if [ -n "${CLAUDE_BIN_DIR:-}" ]; then
    export PATH="$CLAUDE_BIN_DIR:$PATH"
fi

RAW_DATA_PATH="${RAW_DATA_PATH:-$SCRIPT_DIR/data/raw/ippl}"
if [ ! -d "$RAW_DATA_PATH" ]; then
    echo "Raw data directory not found at $RAW_DATA_PATH." >&2
    echo "Clone the IPPL source tree there before submitting the job." >&2
    exit 1
fi

# Fail fast with a clear message if a required CLI is missing in the job env.
for bin in ollama litellm claude; do
    command -v "$bin" >/dev/null 2>&1 || {
        echo "ERROR: '$bin' not on PATH inside the job." >&2
        [ "$bin" = "litellm" ] && echo "  Install into the venv: pip install 'litellm[proxy]'" >&2
        [ "$bin" = "claude" ]  && echo "  Install Claude Code, or export CLAUDE_BIN_DIR=/path/to/dir-containing-claude" >&2
        exit 1
    }
done

# Hand off to the orchestrator. EVAL_MODELS / PER_QUESTION_TIMEOUT / etc. set at
# submit time are forwarded by SLURM and honored by run_eval_ssh.sh.
echo "Launching run_eval_ssh.sh ..."
exec "$SCRIPT_DIR/run_eval_ssh.sh"
