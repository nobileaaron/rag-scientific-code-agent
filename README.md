# RAG Scientific Code Agent

A Retrieval-Augmented Generation (RAG) system for understanding large scientific
C++ codebases, currently focused on the [IPPL](https://github.com/IPPL-framework/ippl)
framework.

The agent ingests source code and documentation, builds a **multi-granular structural
representation** of the codebase, embeds retrievable units at several abstraction
levels, and uses an LLM to answer questions about architecture, file roles,
workflows, and implementation details.

---

## Why multi-granular retrieval

A naive code RAG retrieves only function-sized chunks. That works for "where is X
implemented?" but falls apart on "what does this file do?" or "how does this
workflow fit together?". This system instead builds and retrieves **five levels of
context** from the same vector store:

| Level | One entity per… | Good for |
|---|---|---|
| **Function / symbol** | function, method, class, struct (bodies may be sub-chunked) | "Where is `deleteAllBuffers` implemented?" |
| **Documentation** | documentation section | conceptual / narrative questions |
| **File** | whole file (symbol-aggregated, with raw-content fallback) | "What does `Ippl.h` do?" |
| **Module** | module / folder (aggregates descendant files) | "What lives in the FFT module?" |
| **Call-chain** | callable symbol + its local call neighborhood | "How does FFT work in IPPL?" |

A structural layer (files, modules, symbols, and include/call/ownership/inheritance
edges) ties these levels together so retrieval can expand from a seed hit to its
structurally related neighbors.

---

## Architecture

### Build-time pipeline

```
file_reader → parsers → explanation_generator → structure builders
   → chunkers / entity builders → embedder → vector_store
```

1. **Ingestion** (`src/ingestion/`) — `FileReader` loads `.cpp`/`.h`/`.hpp` and
   documentation; tree-sitter-based parsers turn them into entity dicts.
2. **Explanation generation** (`src/ingestion/explanation_generator.py`) — an LLM
   enriches each parsed entity with a natural-language explanation before chunking,
   at the function, documentation, file, module, and call-chain levels.
3. **Structure building** (`src/structure/`) — `ProjectStructureBuilder` produces a
   graph of files, modules, symbols, and relationships.
4. **Multi-granular entity builders** — file-, module-, and call-chain-level
   builders produce higher-level retrievable entities alongside the raw chunks.
5. **Embedding & vector store** (`src/ingestion/embedder.py`,
   `src/retrieval/vector_store.py`) — FAISS-backed, persisted with a manifest.

### Query-time flow

```
query → query_embed → retriever → reranker → query_intent_router
   → structural_expander → supplementary retrieval → llm_agent → answer LLM
```

`Retriever` runs dense search, then a metadata-aware `Reranker` (with exact
filename/symbol injection), a `QueryIntentRouter`, a `StructuralExpander` that pulls
related entities across levels, and a supplementary retrieval pass. `LLMAgent` builds
the final prompt from the retrieved context and calls the answer LLM.

---

## Requirements

- **Python 3.11** (the cluster launcher pins `Python/3.11.11`)
- **[Ollama](https://ollama.com/)** running locally, for the default embedding and
  LLM backend — or an **Anthropic API key** if you opt any role onto Claude
  (see [Using Anthropic models](#using-anthropic-models))
- A **GPU node** for the initial build — ingestion is GPU-bound. At minimum a single
  GPU able to serve the default 32B-q4 model (~24–48 GB VRAM, A6000 / A100-40G class)

- **tree-sitter** for code parsing (installed via `requirements.txt`; startup fails
  fast if it is unavailable)
- The **IPPL source tree** (not checked in — see [Data prerequisite](#data-prerequisite))

Python dependencies are pinned in [`requirements.txt`](requirements.txt):
FAISS, NumPy, `langchain-community`, `ollama`, `anthropic`, `sentence-transformers`,
and the tree-sitter packages.

---

## Installation

```bash
git clone https://github.com/nobileaaron/rag-scientific-code-agent
cd rag-scientific-code-agent

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Data prerequisite

The IPPL source tree is **not** included in this repository (`data/raw/` is
gitignored). Clone it into the path that `raw_data_path` points at in
[`config/runtime_settings.json`](config/runtime_settings.json):

```bash
git clone https://github.com/IPPL-framework/ippl.git data/raw/ippl
```

### Model backends

By default the system uses Ollama for both embeddings and generation. Pull the models
referenced in `config/runtime_settings.json` before the first run, e.g.:

```bash
ollama pull nomic-embed-text                       # embeddings
ollama pull qwen2.5-coder:32b-instruct-q4_K_M      # answering + entity explanations
```

---

## Running the system

```bash
python main.py          # full pipeline, then drops into the interactive QA loop
```

Or use the repo-local launcher (wraps `main.py` with a fixed venv interpreter):

```bash
./run_main.sh
```

`main.py` reads [`config/runtime_settings.json`](config/runtime_settings.json) once at
startup. There are no CLI flags — all behavior is configured there.

> **Run the first build on a GPU node — ingestion is the expensive part.** It
> generates LLM explanations for every entity at five levels (thousands of calls on
> the default ~32B model). Use at least a single 32B-capable GPU (the `job.sh` SLURM
> launcher targets one). Afterward, explanation snapshots and the vector store are
> cached, so re-runs and interactive querying are far lighter. To cut ingestion cost,
> set `chunk_explanation_model` to a smaller model or point the heavy roles at a
> hosted API.

### Interactive loop

Once the pipeline is ready you get a `Query:` prompt:

| Command | Effect |
|---|---|
| *(any question)* | retrieve context and answer |
| `:debug on` / `:debug off` | toggle retrieval and prompt diagnostics |
| `exit` / `quit` | leave |

The debug report shows the candidate pool size, exact filename/symbol matches, the
detected query intent, the structural-expansion mode, the top reranked candidates,
and the final retrieved context grouped by retrieval role.

### Running on SLURM (gwendolen GPU partition)

[`job.sh`](job.sh) is a SLURM launcher that starts an Ollama server, pulls any
missing models named in the settings file, and then runs `main.py`:

```bash
sbatch job.sh
```

It honors `FORCE_CLEAN_REBUILD=1` (the default), which wipes
`embeddings/vector_store`, `embeddings/project_structure`, and
`embeddings/explanations` before the run. Set `FORCE_CLEAN_REBUILD=0` to reuse
persisted artifacts.

> If you switch the embedding backend to `sentence_transformer`, the compute nodes
> run offline (`HF_HUB_OFFLINE=1`) and can't download the model. Run
> [`precache_hf_model.sh`](precache_hf_model.sh) **once on the login node** first to
> fetch the model into the shared Hugging Face cache. The default `ollama` backend
> doesn't need this — Ollama pulls its own embedding model inside `job.sh`.

---

## Configuration

All knobs live in [`config/runtime_settings.json`](config/runtime_settings.json):
parser choice, chunk size, embedding backend (`ollama` vs `sentence_transformer`),
prompt modes, per-stage LLM models, entity strategies, and retrieval
`candidate_k` / `supplementary_k`.

Each entry under `models` is either a **plain string** (an Ollama model) or a **dict**
selecting a provider:

```jsonc
"models": {
  "answer_model": "qwen2.5-coder:32b-instruct-q4_K_M",
  "answer_model": {"provider": "anthropic", "name": "claude-opus-4-8", "max_tokens": 4096}
}
```

Optional dict keys: `max_tokens`, `system`, `thinking`, `effort`
(`"low"|"medium"|"high"|"xhigh"|"max"`).

### Using Anthropic models

Anthropic-backed roles require `ANTHROPIC_API_KEY` in the environment — there is no
config field for the key by design (only `src/llm/llm_wrapper.py` reads it, via the
official SDK). Export it before `sbatch job.sh`; SLURM forwards the submitter's
environment by default, and the job script fails fast if a Claude model is configured
but the key is missing.

A detailed walkthrough (getting a key, exporting it locally and on the cluster,
spend limits, and which roles to opt in first) lives in
[`docs/ANTHROPIC_API_KEY_SETUP.md`](docs/ANTHROPIC_API_KEY_SETUP.md).

---

## Generated artifacts & caching

A rebuild produces these (all under `embeddings/`, which is gitignored):

- `embeddings/project_structure/project_structure.json` — the structural graph
  (`files`, `modules`, `symbols`, `relationships`, `indexes`, `status`, `summary`)
- `embeddings/project_structure/{file,module,call_chain}_level_entities.json`
- `embeddings/vector_store/` — FAISS index, vectors, metadata, and a manifest

There are **two cache layers** — know which one you're busting:

- **Vector store manifest** — on startup, the stored manifest is compared against the
  current settings. Any difference (parser type, chunk size, embedding model, prompt
  signatures, model names, entity strategies) rebuilds the whole store. When a rebuild
  misbehaves, check the printed *Stored manifest* vs *Expected manifest* diff first.
- **Explanation snapshots** (`embeddings/explanations/*.json`) — generated
  explanations are cached per-entity by a stable key and reused even across a full
  vector-store rebuild, so the LLM only re-runs on new or changed entities. Delete a
  snapshot file to force regeneration at that level.

Prompt templates in [`src/prompts/prompt_templates.py`](src/prompts/prompt_templates.py)
each carry a *signature* that participates in the manifest. Changing a template's text
without bumping its signature will **not** trigger a rebuild.

---

## Repository layout

```text
rag-scientific-code-agent/
├── main.py                       # single entry point: full pipeline + QA loop
├── run_main.sh                   # local launcher (fixed venv interpreter)
├── job.sh                        # SLURM launcher for the gwendolen GPU partition
├── requirements.txt
├── config/runtime_settings.json  # all runtime configuration
├── data/raw/ippl/                # external IPPL source (not checked in)
├── embeddings/                   # generated artifacts (gitignored)
├── docs/                         # API-key setup + evaluation reports
├── experiments/                  # benchmark / manual question sets
├── scripts/                      # evaluation + report generation
└── src/
    ├── ingestion/                # file_reader, parsers, chunkers, explanation_generator, embedder
    ├── structure/                # project_structure_builder, call_graph + entity builders
    ├── retrieval/                # vector_store, retriever, reranker, intent router, expander, debugger
    ├── prompts/                  # prompt_templates (signature-tracked)
    ├── llm/                      # llm_wrapper (Ollama / Anthropic)
    ├── agent/                    # llm_agent (final context assembly + answer)
    └── utils/
```

---

## Evaluation

The `docs/evaluations/` and `scripts/` directories hold an evaluation harness used to
compare models on an IPPL question set
([`docs/evaluations/eval_questions_v2.json`](docs/evaluations/eval_questions_v2.json)).
One track drives **Claude Code** with local Ollama models (via a LiteLLM proxy that
re-exposes them as an Anthropic-compatible endpoint) and grades the answers against
reference solutions. See
[`docs/evaluations/CLAUDE_CODE_EVAL.md`](docs/evaluations/CLAUDE_CODE_EVAL.md) for how
the pieces fit together.

---

## License

Licensed under the Apache License 2.0 — see [`LICENSE`](LICENSE).
