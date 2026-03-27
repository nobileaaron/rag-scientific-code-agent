# Project Overview

This document gives a practical overview of the repository structure as it exists right now.

## Purpose

The project is a retrieval-augmented code understanding system for scientific C++ codebases, currently focused on IPPL.

At a high level, it:

1. loads source code and documentation
2. parses code into entities
3. builds a structural project graph
4. generates higher-level retrieval entities
5. embeds retrievable records
6. answers questions with retrieval plus an LLM

## Top-Level Layout

```text
rag-scientific-code-agent/
├── main.py
├── run_main.sh
├── requirements.txt
├── README.md
├── PROJECT_OVERVIEW.md
├── config/
├── configs/
├── data/
├── embeddings/
├── experiments/
├── report/
├── src/
└── test1/
```

## Main Entry Point

- [`main.py`](/Users/aaron/semester_project/rag-scientific-code-agent/main.py)
  Orchestrates the full runtime:
  loading settings, reading files, parsing code, building structure, rebuilding or loading the vector store, and starting the interactive QA loop.

- [`run_main.sh`](/Users/aaron/semester_project/rag-scientific-code-agent/run_main.sh)
  Convenience launcher for running the project with the intended Python interpreter.

## Configuration

- [`config/runtime_settings.json`](/Users/aaron/semester_project/rag-scientific-code-agent/config/runtime_settings.json)
  Main runtime settings file. Controls parser choice, explanation settings, embedding backend, prompt modes, model names, and retrieval settings.

- `configs/`
  Reserved for additional configuration. It exists in the repo layout but is not the main active runtime entry point right now.

## Data and Outputs

- `data/raw/ippl/`
  Expected location of the external IPPL codebase that gets ingested.

- `data/processed/`
  Reserved for processed data outputs if needed later.

- `embeddings/project_structure/`
  Stores structure snapshots and higher-level generated entities.
  Current important artifact:
  - [`embeddings/project_structure/project_structure.json`](/Users/aaron/semester_project/rag-scientific-code-agent/embeddings/project_structure/project_structure.json)

- `embeddings/vector_store/`
  Stores the persisted FAISS index, vectors, metadata, and manifest used by retrieval.

- `experiments/`
  Benchmark and manual question sets used for testing retrieval and answer quality.
  Current files:
  - [`experiments/benchmark_questions.json`](/Users/aaron/semester_project/rag-scientific-code-agent/experiments/benchmark_questions.json)
  - [`experiments/manual_questions.json`](/Users/aaron/semester_project/rag-scientific-code-agent/experiments/manual_questions.json)

- `report/`
  Reserved for report-related material.

## Source Tree

The active code lives under `src/`.

### `src/ingestion`

Handles loading, parsing, chunking, explanation generation, and embedding.

- [`src/ingestion/file_reader.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/file_reader.py)
  Loads source and documentation files.

- [`src/ingestion/explanation_generator.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/explanation_generator.py)
  Generates entity-level explanations before chunking.

- [`src/ingestion/embedder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/embedder.py)
  Builds embeddings using the configured backend.

Subareas:

- `src/ingestion/code/`
  C++/header parsing and chunking.
  Main files:
  - [`src/ingestion/code/cpp_parser.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/cpp_parser.py)
  - [`src/ingestion/code/header_parser.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/header_parser.py)
  - [`src/ingestion/code/cpp_function_chunker.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/cpp_function_chunker.py)
  - [`src/ingestion/code/header_chunker.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/header_chunker.py)
  - [`src/ingestion/code/reference_extractor.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/reference_extractor.py)
  - [`src/ingestion/code/comment_extractor.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/comment_extractor.py)

- `src/ingestion/documentation/`
  Documentation parsing and chunking.
  Main files:
  - [`src/ingestion/documentation/doc_parser.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/documentation/doc_parser.py)
  - [`src/ingestion/documentation/doc_chunker.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/documentation/doc_chunker.py)

### `src/structure`

Builds the structural project representation and the higher-level retrieval entities.

- [`src/structure/project_structure_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/project_structure_builder.py)
  Builds the project snapshot with files, modules, symbols, relationships, indexes, status, and summary.

- [`src/structure/call_graph_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/call_graph_builder.py)
  Extracts approximate call edges from parsed code.

- [`src/structure/file_level_entity_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/file_level_entity_builder.py)
  Builds one file-level retrieval entity per file, with symbol-aggregated and raw-content fallback modes.

- [`src/structure/module_level_entity_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/module_level_entity_builder.py)
  Builds module-level retrieval entities by aggregating descendant files.

- [`src/structure/call_chain_entity_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/call_chain_entity_builder.py)
  Builds call-chain entities around callable symbols and their local neighborhoods.

### `src/retrieval`

Implements vector storage, candidate retrieval, reranking, routing, structural expansion, and debug reporting.

- [`src/retrieval/vector_store.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/vector_store.py)
  FAISS-backed persistent vector store.

- [`src/retrieval/retriever.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/retriever.py)
  Main retrieval pipeline.

- [`src/retrieval/reranker.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/reranker.py)
  Metadata-aware reranking and exact filename/symbol handling.

- [`src/retrieval/query_intent_router.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/query_intent_router.py)
  Chooses retrieval-expansion behavior based on query type.

- [`src/retrieval/structural_expander.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/structural_expander.py)
  Expands seed retrieval with related file/module/call-chain/function context.

- [`src/retrieval/debugger.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/debugger.py)
  Prints retrieval diagnostics and final selected context in debug mode.

### `src/prompts`

- [`src/prompts/prompt_templates.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/prompts/prompt_templates.py)
  Stores prompt templates for:
  - entity explanations
  - retrieval-time answering
  - file-level explanations
  - file fallback explanations
  - module-level explanations
  - call-chain explanations

### `src/llm`

- [`src/llm/llm_wrapper.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/llm/llm_wrapper.py)
  Thin wrapper around the configured LLM backend currently used by the pipeline.

### `src/agent`

- [`src/agent/llm_agent.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/agent/llm_agent.py)
  Builds final retrieved context and requests the final answer from the model.

### `src/utils`

- [`src/utils/helpers.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/utils/helpers.py)
  Small utility/helper code.

### `src/evaluation`

This directory exists but is currently not a major active part of the main runtime path.

## Retrieval Levels

The current system retrieves across multiple abstraction levels:

- function/symbol level
- documentation chunk level
- file level
- module level
- call-chain level

This is one of the main architectural shifts compared with a pure function-chunk RAG baseline.

## Runtime Flow

The current runtime flow is:

```text
runtime_settings
  -> file_reader
  -> code/doc parsers
  -> explanation generation
  -> project structure builder
  -> file/module/call-chain entity builders
  -> chunkers
  -> embedder
  -> vector store
  -> retriever
  -> llm_agent
```

More concretely:

1. [`main.py`](/Users/aaron/semester_project/rag-scientific-code-agent/main.py) loads settings
2. files are read from `data/raw/ippl`
3. code and docs are parsed into entities
4. the project graph is built and saved
5. if needed, explanations and higher-level entities are generated
6. retrievable records are embedded and stored
7. interactive question answering begins

## Current Practical Notes

- The project expects the external IPPL source tree under `data/raw/ippl/`.
- The vector store is rebuild-sensitive to changes in runtime settings and prompt signatures.
- The repo currently supports both `ollama` and `sentence_transformer` embedding backends.
- The LLM/explanation pipeline is currently tightly connected to the configured runtime backend.

## Suggested Reading Order

If you want to understand the project quickly, read in this order:

1. [`README.md`](/Users/aaron/semester_project/rag-scientific-code-agent/README.md)
2. [`main.py`](/Users/aaron/semester_project/rag-scientific-code-agent/main.py)
3. [`config/runtime_settings.json`](/Users/aaron/semester_project/rag-scientific-code-agent/config/runtime_settings.json)
4. [`src/structure/project_structure_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/project_structure_builder.py)
5. [`src/retrieval/retriever.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/retriever.py)
6. [`src/agent/llm_agent.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/agent/llm_agent.py)
