#!/usr/bin/env bash
#
# run_eval_ssh.sh — one-shot launcher for the Claude Code model-matrix eval.
#
# It wires up:   Claude Code  ->  LiteLLM proxy (/v1/messages)  ->  Ollama
#
# and runs every IPPL eval question (docs/evaluations/eval_questions_v2.json)
# through each local model, writing answers to docs/evaluations/answers/.
#
# Designed to be run over SSH (or under `sbatch`) on a GPU box:
#
#     ./run_eval_ssh.sh
#
# Override anything via environment variables — see the CONFIG block below.
#
# Prereqs on the box:
#   * ollama        (https://ollama.com)            -> `ollama --version`
#   * litellm proxy (`pip install 'litellm[proxy]'`) -> `litellm --version`
#   * claude code   (npm i -g @anthropic-ai/claude-code) -> `claude --version`
#   * the IPPL source cloned into data/raw/ippl
#   * the Ollama model tags in litellm_ollama_config.yaml must exist
#     (`ollama list`); pull them or let this script pull them.

set -euo pipefail

# --------------------------------------------------------------------------
# CONFIG (override with env vars)
# --------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
LITELLM_CONFIG="${LITELLM_CONFIG:-$SCRIPT_DIR/litellm_ollama_config.yaml}"
LITELLM_PORT="${LITELLM_PORT:-4000}"
LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-sk-local}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
RAW_DATA_PATH="${RAW_DATA_PATH:-$SCRIPT_DIR/data/raw/ippl}"

# Ollama tags to make sure are present before the run. Must match the
# `model:` tags referenced in $LITELLM_CONFIG. Override with a space-separated
# string, e.g.  OLLAMA_MODELS="qwen2.5-coder:7b-instruct-q4_K_M gemma4:12b"
DEFAULT_OLLAMA_MODELS="qwen2.5-coder:7b-instruct-q4_K_M qwen2.5-coder:32b-instruct-q4_K_M qwen3.5:9b gemma4:12b"
# shellcheck disable=SC2206
OLLAMA_MODELS_TO_PULL=( ${OLLAMA_MODELS:-$DEFAULT_OLLAMA_MODELS} )

# Optional: restrict which model labels to run, e.g.
#   EVAL_MODELS="qwen25_7b_q4km gemma4_12b" ./run_eval_ssh.sh
EVAL_MODELS="${EVAL_MODELS:-}"
PER_QUESTION_TIMEOUT="${PER_QUESTION_TIMEOUT:-1800}"
ALLOWED_TOOLS="${ALLOWED_TOOLS:-Read,Grep,Glob}"

OLLAMA_LOG="${OLLAMA_LOG:-$SCRIPT_DIR/ollama.log}"
LITELLM_LOG="${LITELLM_LOG:-$SCRIPT_DIR/litellm.log}"

# --------------------------------------------------------------------------
# Sanity checks
# --------------------------------------------------------------------------
need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' not found on PATH. $2" >&2; exit 1; }; }
need ollama  "Install from https://ollama.com"
need litellm "Install with: pip install 'litellm[proxy]'"
need claude  "Install with: npm install -g @anthropic-ai/claude-code"
need curl    "Install curl."

if [ ! -d "$RAW_DATA_PATH" ]; then
    echo "ERROR: IPPL source not found at $RAW_DATA_PATH" >&2
    echo "Clone the IPPL tree there before running." >&2
    exit 1
fi

# --------------------------------------------------------------------------
# Process management / cleanup
# --------------------------------------------------------------------------
OLLAMA_PID=""
LITELLM_PID=""
STARTED_OLLAMA=0

cleanup() {
    [ -n "$LITELLM_PID" ] && kill "$LITELLM_PID" 2>/dev/null || true
    if [ "$STARTED_OLLAMA" = "1" ] && [ -n "$OLLAMA_PID" ]; then
        kill "$OLLAMA_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

# --------------------------------------------------------------------------
# 1. Ollama
# --------------------------------------------------------------------------
export OLLAMA_HOST="127.0.0.1:${OLLAMA_PORT}"
if curl -sf "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1; then
    echo "Ollama already running on :${OLLAMA_PORT}."
else
    echo "Starting Ollama server (log: $OLLAMA_LOG)..."
    ollama serve >>"$OLLAMA_LOG" 2>&1 &
    OLLAMA_PID=$!
    STARTED_OLLAMA=1
    for _ in $(seq 1 60); do
        curl -sf "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1 && break
        sleep 2
    done
    curl -sf "http://127.0.0.1:${OLLAMA_PORT}/api/tags" >/dev/null 2>&1 \
        || { echo "ERROR: Ollama did not become ready." >&2; exit 1; }
    echo "Ollama is ready."
fi

echo "Ensuring required Ollama models are present..."
for tag in "${OLLAMA_MODELS_TO_PULL[@]}"; do
    if ollama show "$tag" >/dev/null 2>&1; then
        echo "  present: $tag"
    else
        echo "  pulling: $tag"
        ollama pull "$tag"
    fi
done

# --------------------------------------------------------------------------
# 2. LiteLLM proxy
# --------------------------------------------------------------------------
echo "Starting LiteLLM proxy on :${LITELLM_PORT} (log: $LITELLM_LOG)..."
litellm --config "$LITELLM_CONFIG" --port "$LITELLM_PORT" --host 127.0.0.1 \
    >>"$LITELLM_LOG" 2>&1 &
LITELLM_PID=$!

echo "Waiting for the proxy to serve /v1/models..."
proxy_ready=0
for _ in $(seq 1 60); do
    code=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
        "http://127.0.0.1:${LITELLM_PORT}/v1/models" || true)
    if [ "$code" = "200" ]; then proxy_ready=1; break; fi
    if ! kill -0 "$LITELLM_PID" 2>/dev/null; then
        echo "ERROR: LiteLLM proxy exited early. Last log lines:" >&2
        tail -n 30 "$LITELLM_LOG" >&2 || true
        exit 1
    fi
    sleep 2
done
[ "$proxy_ready" = "1" ] || { echo "ERROR: proxy never became ready." >&2; tail -n 30 "$LITELLM_LOG" >&2 || true; exit 1; }
echo "LiteLLM proxy is ready. Models exposed:"
curl -s -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
    "http://127.0.0.1:${LITELLM_PORT}/v1/models" \
    | "$PYTHON_BIN" -c "import json,sys;[print('  -',m['id']) for m in json.load(sys.stdin).get('data',[])]" 2>/dev/null || true

# --------------------------------------------------------------------------
# 3. Point Claude Code at the proxy and run the eval
# --------------------------------------------------------------------------
export ANTHROPIC_BASE_URL="http://127.0.0.1:${LITELLM_PORT}"
export ANTHROPIC_AUTH_TOKEN="${LITELLM_MASTER_KEY}"
export ANTHROPIC_API_KEY="${LITELLM_MASTER_KEY}"
# Skip the interactive first-run / API-key helper in headless mode.
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1

echo "Running the model matrix..."
RUN_ARGS=(--timeout "$PER_QUESTION_TIMEOUT" --allowed-tools "$ALLOWED_TOOLS")
if [ -n "$EVAL_MODELS" ]; then
    # shellcheck disable=SC2206
    RUN_ARGS+=(--models $EVAL_MODELS)
fi

"$PYTHON_BIN" "$SCRIPT_DIR/scripts/run_claude_code_model_matrix.py" "${RUN_ARGS[@]}"

echo "Done. Answers are in docs/evaluations/answers/ (claude_code_*.json)."
