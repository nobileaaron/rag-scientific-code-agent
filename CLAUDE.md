# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the system

- `python main.py` — runs the full pipeline and drops into the interactive QA loop.
- `./run_main.sh` — wraps `main.py` with the user's local `.venv` Python interpreter (`/Users/aaron/semester_project/.venv/bin/python`).
- `sbatch job.sh` — SLURM launcher for the gwendolen GPU partition. Starts an Ollama server, pulls any missing models named in `config/runtime_settings.json`, then runs `main.py`. Honors `FORCE_CLEAN_REBUILD=1` (default) to wipe `embeddings/vector_store`, `embeddings/project_structure`, and `embeddings/explanations` before the run.
- In the interactive loop: `:debug on` / `:debug off` toggle retrieval diagnostics, `exit` / `quit` leave.

There is no test runner, linter, or build step in this repo — `main.py` is the only entry point.

## Data prerequisite

The IPPL source tree is not checked in. Clone it into `data/raw/ippl` before running (`raw_data_path` in `config/runtime_settings.json` points there). `data/raw/` is gitignored.

## Runtime configuration

All knobs live in `config/runtime_settings.json` — parser choice, chunk size, embedding backend (`ollama` vs `sentence_transformer`), prompt modes, per-stage LLM models, entity strategies, and retrieval `candidate_k`/`supplementary_k`. `main.py` reads this once at startup; there are no CLI flags.

Each entry under `models` can be either:

- A plain string (treated as an Ollama model): `"answer_model": "qwen2.5-coder:32b-instruct-q4_K_M"`
- A dict selecting a provider: `"answer_model": {"provider": "anthropic", "name": "claude-opus-4-7", "max_tokens": 4096}`. Optional dict keys: `max_tokens`, `system`, `thinking` (e.g. `{"type": "adaptive"}` for Opus 4.7), `effort` (`"low"|"medium"|"high"|"xhigh"|"max"`).

Anthropic entries require `ANTHROPIC_API_KEY` in the environment. Export it before `sbatch job.sh`; SLURM forwards the submitter's env by default. The job script fails fast if an anthropic model is configured and the key is missing. Switching a role between providers changes its manifest key (`"{provider}:{name}"`), which invalidates the vector store and triggers a rebuild.

## Architecture

The pipeline is staged and each stage's output feeds the next. Understanding the flow in `main.py` (lines ~391–721) is the fastest way to orient:

1. **Ingestion** (`src/ingestion/`) — `FileReader` loads `.cpp`/`.h`/`.hpp` and documentation; parsers (`cpp_parser`, `header_parser`, `doc_parser`) turn them into entity dicts. Parser type is `tree_sitter` with a silent fallback to `regex` if tree-sitter is unavailable (`resolve_parser_type`).
2. **Explanation generation** (`src/ingestion/explanation_generator.py`) — an LLM enriches each parsed entity with a natural-language explanation before chunking. Runs at multiple levels: function, documentation section, file, module, call-chain.
3. **Structure building** (`src/structure/`) — `ProjectStructureBuilder` produces a graph of files, modules, symbols, and relationships (include/call/ownership/inheritance edges). Saved to `embeddings/project_structure/project_structure.json`.
4. **Multi-granular entity builders** — `FileLevelEntityBuilder`, `ModuleLevelEntityBuilder`, `CallChainEntityBuilder` produce higher-level retrievable entities alongside the raw function/header/doc chunks. All five levels go into the same vector store.
5. **Embedding & vector store** (`src/ingestion/embedder.py`, `src/retrieval/vector_store.py`) — FAISS-backed, persisted under `embeddings/vector_store/` with a manifest.
6. **Retrieval** (`src/retrieval/`) — `Retriever` = dense search → `Reranker` (metadata-aware, exact filename/symbol injection) → `QueryIntentRouter` → `StructuralExpander` (pulls related entities across levels) → supplementary retrieval.
7. **Answering** (`src/agent/llm_agent.py`, `src/llm/llm_wrapper.py`) — builds the final prompt from retrieved context using templates in `src/prompts/prompt_templates.py` and calls the answer LLM.

### Two cache layers — know which one you're busting

- **Vector store manifest** (`build_vector_store_manifest` in `main.py`). On startup, `load_persisted_vector_store` compares the stored manifest against the current settings. If anything in the manifest differs (parser type, chunk size, embedding model, any prompt signature or model name, entity strategies), the whole store is rebuilt from scratch. Prompt signatures allow limited compatibility via `get_compatible_prompt_template_signatures` — changing a prompt's *text* without bumping its signature will not trigger a rebuild.
- **Explanation snapshots** (`embeddings/explanations/*.json`). Generated explanations are cached per-entity by a stable key (`build_explanation_snapshot_key`). Even on a full vector-store rebuild, existing snapshots are reused so you only re-run the LLM on new or changed entities. Delete the relevant snapshot file to force regeneration at a given level.

When a rebuild misbehaves, check the printed "Stored manifest" vs "Expected manifest" diff before touching code — it usually points at the offending setting.

### Prompt templates

`src/prompts/prompt_templates.py` exposes templates by mode (`retrieval_answer`, `general`, `file_level`, `file_level_fallback`, `module_level`, `call_chain`). Each template has a *signature* that participates in the vector store manifest. If you change a template in a non-cosmetic way, bump its signature so downstream artifacts rebuild.

## Context files

`README.md` and `PROJECT_OVERVIEW.md` contain more narrative background on use cases and the file layout; both are kept up to date with the current code.
