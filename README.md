# RAG Scientific Code Agent

Retrieval-Augmented Generation system for scientific C++ code understanding, currently focused on the IPPL codebase.

The project ingests source code and documentation, builds a multi-granular structural representation of the codebase, embeds retrievable units at several levels, and uses an LLM to answer questions about architecture, file roles, workflows, and implementation details.

## Overview

The current system supports:

- C++ source and header ingestion
- documentation ingestion
- entity-level explanation generation with an LLM
- dense retrieval with metadata-aware reranking
- exact filename and symbol injection
- structural expansion after seed retrieval
- multi-granular retrieval across function/symbol, file, module, and call-chain levels

The main target use cases are questions like:

- What does `Ippl.h` do?
- Where is `deleteAllBuffers` implemented?
- What does the `Communicate` module do?
- How does FFT work in IPPL?

## Current Architecture

At a high level, the runtime flow is:

1. Load runtime settings from [`config/runtime_settings.json`](/Users/aaron/semester_project/rag-scientific-code-agent/config/runtime_settings.json)
2. Load raw source and documentation files
3. Parse source files into code entities
4. Build the project structure graph
5. If needed, generate entity explanations and build retrievable artifacts
6. Embed the retrievable records and persist the vector store
7. Answer user queries through retrieval + LLM synthesis

The main pipeline now looks like:

`file_reader -> parsers -> explanation_generator -> structure builders -> chunkers/entity builders -> embedder -> vector_store -> retriever -> llm_agent`

The query-time flow looks like:

`query -> query_embed -> retriever -> reranker -> structural_expander -> llm_agent -> answer LLM`

## Multi-Granular Retrieval

The system no longer retrieves only function chunks. It now builds and retrieves multiple levels of context:

- **Function / symbol level**
  parsed functions, methods, declarations, classes, and structs.
  Function and method bodies may be split into smaller chunks.

- **File level**
  One whole-file entity per file.
  Uses either aggregated symbol summaries or raw-content fallback if no symbols were detected.

- **Module level**
  One entity per module/folder.
  Aggregates descendant files, file-level summaries, and structural facts.

- **Call-chain level**
  One entity per callable symbol with local incoming/outgoing call relationships.
  Summarizes a local workflow neighborhood around that symbol.

## Structural Layer

Before retrieval, the system builds a project structure snapshot and saves it to:

- [`embeddings/project_structure/project_structure.json`](/Users/aaron/semester_project/rag-scientific-code-agent/embeddings/project_structure/project_structure.json)

That structure currently contains:

- `files`
- `modules`
- `symbols`
- `relationships` with `include_edges`, `call_edges`, `ownership_edges`, and `inheritance_edges`
- `indexes`
- `status`
- `summary`

Module hierarchy is scope-aware, so source folders are separated from non-source areas such as tests or CI.

## Generated Artifacts

During a rebuild, the system can produce:

- [`embeddings/project_structure/project_structure.json`](/Users/aaron/semester_project/rag-scientific-code-agent/embeddings/project_structure/project_structure.json)
- [`embeddings/project_structure/file_level_entities.json`](/Users/aaron/semester_project/rag-scientific-code-agent/embeddings/project_structure/file_level_entities.json)
- [`embeddings/project_structure/module_level_entities.json`](/Users/aaron/semester_project/rag-scientific-code-agent/embeddings/project_structure/module_level_entities.json)
- [`embeddings/project_structure/call_chain_entities.json`](/Users/aaron/semester_project/rag-scientific-code-agent/embeddings/project_structure/call_chain_entities.json)
- [`embeddings/vector_store`](/Users/aaron/semester_project/rag-scientific-code-agent/embeddings/vector_store)

The vector store persists:

- embedding vectors
- metadata for all retrievable records
- a manifest describing the runtime settings used to build it

If the manifest changes, the vector store is rebuilt automatically.

## Key Components

### Ingestion

- [`src/ingestion/file_reader.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/file_reader.py)
  - loads C++ source/header files and documentation files

- [`src/ingestion/code/cpp_parser.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/cpp_parser.py)
- [`src/ingestion/code/header_parser.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/header_parser.py)
- [`src/ingestion/documentation/doc_parser.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/documentation/doc_parser.py)
  - parse source code and documentation into structured entities

- [`src/ingestion/explanation_generator.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/explanation_generator.py)
  - generates LLM explanations for parsed entities before chunking

- [`src/ingestion/code/cpp_function_chunker.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/cpp_function_chunker.py)
- [`src/ingestion/code/header_chunker.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/code/header_chunker.py)
- [`src/ingestion/documentation/doc_chunker.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/documentation/doc_chunker.py)
  - turn parsed entities into retrievable chunk records

- [`src/ingestion/embedder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/ingestion/embedder.py)
  - supports `ollama` and `sentence_transformer` embedding backends

### Structure Builders

- [`src/structure/project_structure_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/project_structure_builder.py)
  - builds the project structure graph

- [`src/structure/call_graph_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/call_graph_builder.py)
  - builds approximate call edges using tree-sitter

- [`src/structure/file_level_entity_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/file_level_entity_builder.py)
  - builds whole-file entities

- [`src/structure/module_level_entity_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/module_level_entity_builder.py)
  - builds module/folder entities

- [`src/structure/call_chain_entity_builder.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/structure/call_chain_entity_builder.py)
  - builds local call-chain workflow entities

### Retrieval

- [`src/retrieval/vector_store.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/vector_store.py)
  - FAISS-backed persistent vector store

- [`src/retrieval/reranker.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/reranker.py)
  - metadata-aware reranking
  - exact filename extraction
  - exact symbol extraction

- [`src/retrieval/query_intent_router.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/query_intent_router.py)
  - routes query types such as location, workflow, or file-purpose queries

- [`src/retrieval/structural_expander.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/structural_expander.py)
  - expands seed retrieval results with related entities from other levels

- [`src/retrieval/retriever.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/retriever.py)
  - combines dense retrieval, reranking, structural expansion, and supplementary retrieval

- [`src/retrieval/debugger.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/retrieval/debugger.py)
  - prints a retrieval debug report when debug mode is enabled

### Prompting and LLM Usage

- [`src/prompts/prompt_templates.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/prompts/prompt_templates.py)
  - prompt templates for entity explanations, file-level explanations, file-level fallback explanations, module-level explanations, call-chain explanations, and final retrieval-based answering

- [`src/llm/llm_wrapper.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/llm/llm_wrapper.py)
  - wraps the configured Ollama chat model

- [`src/agent/llm_agent.py`](/Users/aaron/semester_project/rag-scientific-code-agent/src/agent/llm_agent.py)
  - builds final retrieved context and asks the answer LLM

## Runtime Settings

Runtime behavior is configured in:

- [`config/runtime_settings.json`](/Users/aaron/semester_project/rag-scientific-code-agent/config/runtime_settings.json)

That file currently controls:

- parser choice
- chunk size
- explanation generation settings
- embedding backend and embedding model
- prompt modes
- LLM models for all explanation/answer stages
- retrieval settings
- strategy names used for manifest tracking

## Installation

Clone the repository:

```bash
git clone https://github.com/nobileaaron/rag-scientific-code-agent
cd rag-scientific-code-agent
```

The raw IPPL codebase is not included in the repository and needs to be added separately.

Example:

```bash
git clone https://github.com/ippl-framework/ippl.git data/raw/ippl
```

## Running the System

Run with your project Python environment:

```bash
python main.py
```

If you use the repo-local launcher:

```bash
./run_main.sh
```

The exact interpreter and models depend on how your environment is configured. On local development machines or servers, make sure the required Python packages and model backends are available.

## Debugging

Turn retrieval debugging on or off inside the interactive prompt with:

```text
:debug on
:debug off
```

The debug report shows:

- candidate pool size
- exact filename and symbol matches
- query intent
- structural expansion mode
- top reranked candidates
- final retrieved context grouped by retrieval role

## Current Focus

The current architecture is centered on:

- reliable structural understanding of the codebase
- multi-granular retrieval
- explanation generation at several abstraction levels
- better grounding of final answers in retrieved evidence
