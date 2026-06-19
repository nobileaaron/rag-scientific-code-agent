# Claude Code model-matrix evaluation (local models via LiteLLM)

This runs the IPPL eval question set (`docs/evaluations/eval_questions_v2.json`)
through **Claude Code** while Claude Code is driven by **local Ollama models**
instead of the Anthropic API. Each model answers every question by exploring the
IPPL source under `data/raw/ippl` with read-only tools. Answers land in
`docs/evaluations/answers/claude_code_<label>_<timestamp>.json`.

## How the pieces fit together

```
 run_eval_ssh.sh
      │ starts + health-checks
      ▼
 Claude Code (claude -p)  ──/v1/messages──►  LiteLLM proxy  ──►  Ollama
   ANTHROPIC_BASE_URL=:4000                  (:4000)             (:11434)
```

* **Ollama** serves the raw models.
* **LiteLLM proxy** re-exposes them as an Anthropic-compatible `/v1/messages`
  endpoint (that's the protocol Claude Code speaks) and sets a large Ollama
  context window (`num_ctx: 32768`) so the system prompt + tool schemas + the
  files the model reads all fit.
* **Claude Code** is pointed at the proxy with `ANTHROPIC_BASE_URL` /
  `ANTHROPIC_AUTH_TOKEN`.

> The earlier failed run (`API Error: 400 ... Invalid model name`) happened
> because Claude Code reached a LiteLLM proxy that hadn't loaded these model
> definitions. The launcher now starts the proxy with the correct config and
> verifies `/v1/models` before running anything.

## Models

| `--model` name passed to Claude Code | label / output file | Ollama tag |
| --- | --- | --- |
| `claude-qwen25-7b-q4km`  | `qwen25_7b_q4km`  | `qwen2.5-coder:7b-instruct-q4_K_M` |
| `claude-qwen25-32b-q4km` | `qwen25_32b_q4km` | `qwen2.5-coder:32b-instruct-q4_K_M` |
| `claude-qwen35-9b`       | `qwen35_9b`       | `qwen3.5:9b` |
| `claude-gemma4-12b`      | `gemma4_12b`      | `gemma4:12b` |

The Ollama tags must exist on the box (`ollama list`). If yours differ, edit
both `litellm_ollama_config.yaml` (the `model:` lines) and the pull list. The
`qwen3.5:9b` / `gemma4:12b` tags follow the naming already used in this repo's
other eval files — adjust to whatever you actually have installed.

## Prerequisites (one time, on the SSH box)

```bash
ollama --version        # https://ollama.com
litellm --version       # pip install 'litellm[proxy]'
claude --version        # npm install -g @anthropic-ai/claude-code
ls data/raw/ippl        # IPPL source must be cloned here
```

## Run it

From the repo root:

```bash
./run_eval_ssh.sh
```

That will: start Ollama (if not already up), pull any missing models, start the
LiteLLM proxy, wait until it's healthy, point Claude Code at it, and run all
four models over all questions. It cleans up the proxy (and Ollama, if it
started it) on exit. Output: `docs/evaluations/answers/claude_code_*.json`,
written incrementally so a crash keeps finished answers.

Because a full matrix is long-running, use a detachable session over SSH:

```bash
tmux new -s eval        # or: screen
./run_eval_ssh.sh 2>&1 | tee eval_run.log
# detach: Ctrl-b d   (reattach later: tmux attach -t eval)
```

Watch the backing services in other panes:

```bash
tail -f litellm.log
tail -f ollama.log
```

## Useful overrides (environment variables)

```bash
# Only run a subset of models (space-separated labels):
EVAL_MODELS="qwen25_7b_q4km gemma4_12b" ./run_eval_ssh.sh

# Different ports:
LITELLM_PORT=4100 OLLAMA_PORT=11500 ./run_eval_ssh.sh

# Give the agent more time per question (the 32B model is slow):
PER_QUESTION_TIMEOUT=2400 ./run_eval_ssh.sh

# Different Ollama tags to ensure present:
OLLAMA_MODELS="qwen2.5-coder:7b-instruct-q4_K_M gemma4:12b" ./run_eval_ssh.sh

# Specific Python interpreter (e.g. the project venv):
PYTHON_BIN=/Users/aaron/semester_project/.venv/bin/python ./run_eval_ssh.sh
```

## Running the Python step on its own

If the proxy is already up (or you want to manage it yourself), export the proxy
env and call the runner directly:

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:4000
export ANTHROPIC_AUTH_TOKEN=sk-local
export ANTHROPIC_API_KEY=sk-local
python3 scripts/run_claude_code_model_matrix.py --models qwen25_7b_q4km
```

## Tuning the context window

`num_ctx: 32768` in `litellm_ollama_config.yaml` is the Ollama context window.
Bigger context = more VRAM. If a model OOMs on the GPU, lower `num_ctx` (e.g.
16384) for that model; if answers look truncated, the system prompt + files
likely overran the window — raise it (and confirm the model supports it).

## Output format

Each file matches the repo's eval style:

```json
{
  "schema": "claude-code-model-matrix/v1",
  "model": "claude-gemma4-12b",
  "label": "gemma4_12b",
  "run_complete": true,
  "run_metadata": { "...": "host, timestamps, model, timeouts, counts" },
  "questions_source": "docs/evaluations/eval_questions_v2.json",
  "answers": [
    { "id": "file_001", "category": "file_purpose",
      "question": "...", "answer": "...", "error": "", "latency_seconds": 12.3 }
  ]
}
```

## Troubleshooting

* **`API Error: 400 ... Invalid model name`** — the proxy isn't serving that
  model. Check `curl -H "Authorization: Bearer sk-local" http://127.0.0.1:4000/v1/models`
  and that the `model_name` in the config matches the `--model` passed.
* **`claude` hangs / first-run prompt** — Claude Code may want onboarding the
  first time. Run `claude` once interactively on the box to clear it, then
  re-run the script.
* **Proxy exits immediately** — check `litellm.log`; usually a bad model tag or
  a port already in use.
* **Empty answers with `error: timeout`** — raise `PER_QUESTION_TIMEOUT`; the
  32B model is slow, especially at 32k context.
