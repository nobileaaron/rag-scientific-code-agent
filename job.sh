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
SETTINGS_PATH="${SETTINGS_PATH:-$SCRIPT_DIR/config/runtime_settings.json}"

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

echo "Checking configured Ollama models..."
mapfile -t REQUIRED_OLLAMA_MODELS < <(
python - "$SETTINGS_PATH" <<'PY'
import json
import sys

settings_path = sys.argv[1]
with open(settings_path, "r", encoding="utf-8") as f:
    settings = json.load(f)

models = []
if settings.get("embedding", {}).get("backend") == "ollama":
    embedding_model = settings.get("embedding", {}).get("ollama_model")
    if embedding_model:
        models.append(embedding_model)

for key in (
    "answer_model",
    "chunk_explanation_model",
    "file_level_model",
    "module_level_model",
    "call_chain_model",
):
    model_name = settings.get("models", {}).get(key)
    if model_name and model_name not in models:
        models.append(model_name)

for model_name in models:
    print(model_name)
PY
)

for model_name in "${REQUIRED_OLLAMA_MODELS[@]}"; do
    if [ -z "$model_name" ]; then
        continue
    fi

    if ollama show "$model_name" >/dev/null 2>&1; then
        echo "Model already available: $model_name"
        continue
    fi

    echo "Pulling missing model: $model_name"
    ollama pull "$model_name"
done

echo "Running main.py..."
python -u main.py
