#!/bin/bash
#SBATCH --job-name=rag-ippl-eval
#SBATCH --error=gwendolen_eval.error
#SBATCH --output=gwendolen_eval.out
#SBATCH --time=08:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --clusters=gmerlin6
#SBATCH --partition=gwendolen
#SBATCH --account=gwendolen
#SBATCH --gpus=1

# Runs the evaluation question set from docs/evaluations/eval_questions_v2.json
# through the same RAG pipeline used for interactive QA, and saves each
# answer (together with a snapshot of the models + settings that produced it)
# to docs/evaluations/answers/eval_v2_<timestamp>.json.
#
# This mirrors the structure of job.sh: boots an Ollama server, pulls any
# missing configured models, then invokes the evaluation runner instead of
# the interactive main.py loop.
#
# The default behaviour REUSES any persisted vector store that already
# matches the current runtime_settings.json manifest. That way this job
# evaluates the same artifacts produced by the most recent build run.
# If you want a full rebuild before evaluating (e.g. after changing prompt
# templates or model names), submit with:
#     FORCE_CLEAN_REBUILD=1 sbatch eval_job.sh

set -euo pipefail

ulimit -c unlimited

SCRIPT_DIR="${SLURM_SUBMIT_DIR:-$(pwd)}"
SETTINGS_PATH="${SETTINGS_PATH:-$SCRIPT_DIR/config/runtime_settings.json}"
EVAL_ANSWER_MODEL="${EVAL_ANSWER_MODEL:-qwen2.5:72b}"
# Default to reuse-existing so evaluation pairs cleanly with the most recent
# ingest run. Override to 1 if you want to regenerate artifacts here.
FORCE_CLEAN_REBUILD="${FORCE_CLEAN_REBUILD:-0}"
EVAL_QUESTIONS_PATH="${EVAL_QUESTIONS_PATH:-$SCRIPT_DIR/docs/evaluations/eval_questions_v2.json}"
EVAL_RUN_LABEL="${EVAL_RUN_LABEL:-v2}"
if [ -z "${EVAL_OUTPUT_PATH:-}" ]; then
    EVAL_OUTPUT_PATH="$SCRIPT_DIR/docs/evaluations/answers/eval_v2_$(date -u +%Y%m%dT%H%M%SZ).json"
fi

# Adjust these if your cluster environment changes later.
PYTHON_MODULE="${PYTHON_MODULE:-Python/3.11.11}"
OLLAMA_HOME="${OLLAMA_HOME:-/data/user/ext-nobile_a/ollama}"
OLLAMA_LOG="${OLLAMA_LOG:-$SCRIPT_DIR/ollama.log}"
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

TEMP_SETTINGS_PATH="$(mktemp "$SCRIPT_DIR/.eval_runtime_settings.XXXXXX.json")"

cleanup() {
    if [ -n "${OLLAMA_PID:-}" ]; then
        kill "$OLLAMA_PID" 2>/dev/null || true
    fi
    if [ -n "${TEMP_SETTINGS_PATH:-}" ] && [ -f "$TEMP_SETTINGS_PATH" ]; then
        rm -f "$TEMP_SETTINGS_PATH"
    fi
}
trap cleanup EXIT

python - "$SETTINGS_PATH" "$TEMP_SETTINGS_PATH" "$EVAL_ANSWER_MODEL" <<'PY'
import json
import sys

source_path, target_path, answer_model = sys.argv[1:4]

with open(source_path, "r", encoding="utf-8") as f:
    settings = json.load(f)

settings.setdefault("models", {})
settings["models"]["answer_model"] = answer_model

with open(target_path, "w", encoding="utf-8") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY

export RUNTIME_SETTINGS_PATH="$TEMP_SETTINGS_PATH"
EFFECTIVE_SETTINGS_PATH="$TEMP_SETTINGS_PATH"

RAW_DATA_PATH="${RAW_DATA_PATH:-$SCRIPT_DIR/data/raw/ippl}"
if [ ! -d "$RAW_DATA_PATH" ]; then
    echo "Raw data directory not found at $RAW_DATA_PATH." >&2
    echo "Clone the IPPL source tree there before submitting the job." >&2
    exit 1
fi

if [ ! -f "$EVAL_QUESTIONS_PATH" ]; then
    echo "Evaluation questions file not found at $EVAL_QUESTIONS_PATH." >&2
    exit 1
fi

export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

ANTHROPIC_REQUIRED=$(python - "$EFFECTIVE_SETTINGS_PATH" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    settings = json.load(f)

for entry in (settings.get("models") or {}).values():
    if isinstance(entry, dict) and entry.get("provider") == "anthropic":
        print("1")
        break
else:
    print("0")
PY
)

if [ "$ANTHROPIC_REQUIRED" = "1" ] && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "runtime_settings.json references an anthropic model, but ANTHROPIC_API_KEY is not set." >&2
    echo "Export it before running sbatch (e.g. 'export ANTHROPIC_API_KEY=sk-...') so SLURM forwards it to the job." >&2
    exit 1
fi

if [ "$FORCE_CLEAN_REBUILD" = "1" ]; then
    echo "FORCE_CLEAN_REBUILD=1, wiping persisted artifacts before evaluation..."
    rm -rf "$SCRIPT_DIR/embeddings/vector_store"
    rm -rf "$SCRIPT_DIR/embeddings/project_structure"
    rm -rf "$SCRIPT_DIR/embeddings/explanations"
else
    echo "FORCE_CLEAN_REBUILD=0, reusing persisted artifacts when the manifest matches."
fi

echo "Starting Ollama server..."
ollama serve >> "$OLLAMA_LOG" 2>&1 &
OLLAMA_PID=$!

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
python - "$EFFECTIVE_SETTINGS_PATH" <<'PY'
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

def resolve_ollama_name(entry):
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict) and entry.get("provider", "ollama") == "ollama":
        return entry.get("name")
    return None

for key in (
    "answer_model",
    "chunk_explanation_model",
    "file_level_model",
    "module_level_model",
    "call_chain_model",
):
    model_name = resolve_ollama_name(settings.get("models", {}).get(key))
    if model_name and model_name not in models:
        models.append(model_name)

for model_name in models:
    print(model_name)
PY
)

echo "Evaluation answer model override: $EVAL_ANSWER_MODEL"
echo "Effective runtime settings: $EFFECTIVE_SETTINGS_PATH"

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

# If the manifest does not match (or artifacts are missing) the runner will
# abort cleanly with an error. In that case submit with FORCE_CLEAN_REBUILD=1
# to regenerate them inside this job, or run sbatch job.sh first.
if [ ! -d "$SCRIPT_DIR/embeddings/vector_store" ]; then
    if [ "$FORCE_CLEAN_REBUILD" = "1" ]; then
        echo "Rebuilding embeddings/vector_store by running main.py first..."
        RAG_ALLOW_REBUILD=1 python -u main.py <<<'exit'
    else
        echo "No persisted vector store found at embeddings/vector_store." >&2
        echo "Run 'sbatch job.sh' first, or resubmit with FORCE_CLEAN_REBUILD=1 to build here." >&2
        exit 1
    fi
fi

mkdir -p "$SCRIPT_DIR/docs/evaluations/answers"

echo "Running evaluation over ${EVAL_QUESTIONS_PATH}..."
export EVAL_QUESTIONS_PATH
export EVAL_OUTPUT_PATH
export EVAL_RUN_LABEL

python -u scripts/run_rag_evaluation.py
