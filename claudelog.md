# Claude Implementation Log

Running log of notable changes Claude makes to this repo. Newest entries go on top. Each entry should state **what** changed, **why**, and **what the user still needs to do**.

---

## 2026-04-23 — RAG evaluation question set + SLURM runner

**Goal.** Produce a reusable evaluation harness: a categorized question set about the IPPL codebase, plus a gwendolen job that answers every question with the currently configured RAG pipeline and records the models used for the run so results can be scored and compared later.

**Files added.**
- `docs/evaluations/eval_questions_v1.json` — 113 questions across 12 categories (`file_purpose`, `definition_location`, `class_responsibility`, `algorithm`, `data_flow`, `api_usage`, `parallelism_and_kokkos`, `boundary_and_halo`, `numerical_meaning`, `examples_and_miniapps`, `build_and_install`, `testing_and_workflow`). Each entry has `id`, `category`, `question`. Questions were drawn after reading `data/raw/ippl/src/` (Ippl, Field, FFT, Particle, PoissonSolvers, MaxwellSolvers, FEM, Communicate, Meshes, Decomposition, Random, Interpolation), the `alpine/` and `cosmology/` mini-apps, and `doc/extras/*.md` + top-level `README.md` / `WORKFLOW.md` / `INSTALLATION.md`.
- `scripts/run_rag_evaluation.py` — reuses `main.py`'s ingestion/embedding/retrieval setup (by `import main as rag_main`, no REPL) and calls `LLMAgent.answer` on each question. Writes `docs/evaluations/answers/eval_<UTC-timestamp>.json` (override with `EVAL_OUTPUT_PATH`). The output contains `run_metadata` (host, SLURM job id, timestamps, label), `models` (every role with `provider:name` manifest key), full `settings_snapshot`, `vector_store_manifest`, and per-question `{id, category, question, answer, latency_seconds, error}`. Answers are flushed to disk after each question so preemption does not lose progress.
- `eval_job.sh` — gwendolen SLURM script (same boilerplate as `job.sh`: `Python/3.11.11`, Ollama server boot, model-pull loop that skips Anthropic entries, `ANTHROPIC_API_KEY` preflight). Default `FORCE_CLEAN_REBUILD=0` so evaluation reuses the persisted artifacts from the most recent `sbatch job.sh` — this is what pairs the answers cleanly with a specific set of models. Set `FORCE_CLEAN_REBUILD=1` to rebuild inside the eval job.

**Design choices worth remembering.**
- Evaluation runner refuses to build the vector store itself when no usable persisted store exists; it either reuses the existing one or aborts with a clear message. Rebuilding is delegated to `job.sh` so ingestion and evaluation stay separable concerns.
- `models` section in the result JSON normalizes each role via `model_manifest_key()` (same key the vector-store manifest uses). Two result files are directly comparable by model-role.
- `EVAL_RUN_LABEL` is echoed into `run_metadata` — use it to tag runs (e.g. `"qwen32b_v1"`, `"opus47_v1"`) without changing filenames.

**What the user still needs to do.**
1. Make sure `sbatch job.sh` has been run at least once so `embeddings/vector_store/` exists for the current `runtime_settings.json`. Then `sbatch eval_job.sh`.
2. To evaluate a different model, edit `config/runtime_settings.json` (especially `answer_model`), rerun `sbatch job.sh` (or submit `FORCE_CLEAN_REBUILD=1 sbatch eval_job.sh`), then `sbatch eval_job.sh`. The resulting JSON records the exact models used.
3. Optional: tag the run — `EVAL_RUN_LABEL="qwen32b_v1" sbatch eval_job.sh`.
4. After runs finish, pull `docs/evaluations/answers/eval_*.json` off the cluster for scoring/grading.

**Explicit non-goals.**
- No grading/scoring logic — results are raw answers; scoring pass is a separate step.
- No golden/reference answers in the questions file — keeping it a pure question bank so we can score multiple model configurations against a stable set.
- Did not extend `manual_questions.json` / `benchmark_questions.json` in `experiments/`; those capture different metadata (retrieved files, hand-graded scores) and should stay independent of this bulk eval path.

---

## 2026-04-22 — API key setup manual

Added `docs/ANTHROPIC_API_KEY_SETUP.md` — step-by-step guide for getting the key from console.anthropic.com, exporting it persistently on both the Mac (`~/.zshrc`) and gwendolen (`~/.bashrc` + `~/.bash_profile` sourcing fix), security basics (never commit, rotate on exposure), a no-RAG smoke test with a troubleshooting table, and a worked config example flipping only `answer_model` to Anthropic first. Also pinned `anthropic==0.96.0` in `requirements.txt` after confirming the actual installed version (my earlier `0.42.0` guess was wrong).

---

## 2026-04-22 — Anthropic API provider in `LLMWrapper`

**Goal.** Let `runtime_settings.json` pick Claude (Anthropic API) or Ollama on a per-role basis without breaking the existing Ollama-only setup.

**Files changed.**
- `src/llm/llm_wrapper.py` — rewritten. Added `resolve_model_config()` and `model_manifest_key()` helpers, provider dispatch in `LLMWrapper.__init__`, lazy `anthropic` import, and a streaming call path via `client.messages.stream(...)` → `get_final_message()`.
- `main.py` — imported `model_manifest_key`; wrapped all 5 model entries in `build_vector_store_manifest` and the info `print`s so the manifest + logs are consistent whether a role is a string or a dict.
- `requirements.txt` — added `anthropic==0.42.0`.
- `job.sh` — the Ollama-pull loop now filters out Anthropic entries (so it doesn't try `ollama pull claude-opus-4-7`); added a preflight that aborts with a clear message if any role is `provider: anthropic` but `ANTHROPIC_API_KEY` is unset.
- `CLAUDE.md` — Runtime configuration section documents the new dict form.
- `config/runtime_settings.json` — **unchanged on purpose**. Still all Ollama. Opt in per-role when you want.

**Config shape.** Each of `answer_model`, `chunk_explanation_model`, `file_level_model`, `module_level_model`, `call_chain_model` accepts either a bare string (treated as Ollama, backward compat) or:

```json
"answer_model": {
  "provider": "anthropic",
  "name": "claude-opus-4-7",
  "max_tokens": 4096
}
```

Optional dict keys passed through to Anthropic: `max_tokens` (default 4096), `system`, `thinking` (e.g. `{"type": "adaptive"}`), `effort` (`"low"|"medium"|"high"|"xhigh"|"max"`), `extra_headers`.

**Manifest change.** Model entries are normalized to `"{provider}:{name}"` in the vector store manifest (e.g. `"ollama:qwen2.5-coder:32b-instruct-q4_K_M"`, `"anthropic:claude-opus-4-7"`). Switching a role's provider therefore invalidates the vector store — correct behavior. Note: first run after this change rebuilds because the manifest format changed from bare model names to `provider:name`; irrelevant in practice since `FORCE_CLEAN_REBUILD=1` is the default.

**What the user still needs to do.**
1. `pip install anthropic==0.42.0` locally and on the cluster.
2. `export ANTHROPIC_API_KEY=sk-ant-...` before `sbatch job.sh`. SLURM inherits the submitter env (`--export=ALL` is default), so the key flows to the compute node.
3. Verify the gwendolen partition has outbound HTTPS to `api.anthropic.com` before running a long job with an Anthropic role configured.
4. Recommended first step: swap only `answer_model` to Anthropic (one call per interactive query = tiny cost exposure), confirm it works, then consider the others. Hot path is `chunk_explanation_model` (thousands of calls during ingestion) — consider `claude-haiku-4-5` there if Opus is too expensive.

**Explicit non-goals.**
- Embedder stays Ollama (Anthropic has no embedding endpoint).
- No prompt-caching breakpoints yet — revisit if explanation prompts end up sharing a large stable prefix.
- No retry/backoff tuning — the SDK's default retries handle transient failures.
