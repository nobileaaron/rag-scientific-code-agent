#!/bin/bash
#SBATCH --job-name=rag-ippl
#SBATCH --error=gwendolen.error
#SBATCH --output=gwendolen.out
#SBATCH --time=08:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --clusters=gmerlin6
#SBATCH --partition=gwendolen
#SBATCH --account=gwendolen
#SBATCH --gpus=1

set -euo pipefail

ulimit -c unlimited

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(pwd)}"

# Adjust these if your cluster environment changes later.
PYTHON_MODULE="${PYTHON_MODULE:-Python/3.11.11}"
OLLAMA_HOME="${OLLAMA_HOME:-/data/user/ext-nobile_a/ollama}"
OLLAMA_LOG="${OLLAMA_LOG:-$SCRIPT_DIR/ollama.log}"

module load "$PYTHON_MODULE"

export PATH="$OLLAMA_HOME/bin:$PATH"
export OLLAMA_MODELS="${OLLAMA_MODELS:-$OLLAMA_HOME/models}"

cd "$SCRIPT_DIR"
source .venv/bin/activate

echo "Starting Ollama server..."
ollama serve >> "$OLLAMA_LOG" 2>&1 &
OLLAMA_PID=$!

cleanup() {
    if [ -n "${OLLAMA_PID:-}" ]; then
        kill "$OLLAMA_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "Waiting for Ollama to become ready..."
for attempt in $(seq 1 60); do
    if ollama list >/dev/null 2>&1; then
        echo "Ollama is ready."
        break
    fi
    sleep 2
done

if ! ollama list >/dev/null 2>&1; then
    echo "Ollama did not become ready within the expected time."
    exit 1
fi

echo "Running main.py..."
python -u main.py
