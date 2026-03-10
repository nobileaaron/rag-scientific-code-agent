# RAG Scientific Code Agent
Retrieval-Augmented Generation (RAG) system for scientific code understanding of the IPPL (PSI) and OPALX code base.
Upon Inputing a query the system retrieves relevant code files from the IPPL / OPALX framework and uses an LLM to explain algorithms, data flow and the used mathematical methods.

## Overview 
This project builds a RAG-based assistant explaining scientific C++ code.

System:
- Reads in raw data (data/raw/ippl)
- Extracts function chunks
- Parses C++ functions into variables (name, input, output, codebase)
- Generates semantic Embeddings
- Stores embeddings in a FAISS vector database
- Usage of user query to retrieve relevant code base
- Uses LLM (deepseek-codeer) to explain algorithms and numerical logic.

## Architecture

The system follows the depicted RAG pipeline:

file_reader -> chunker -> embedder -> vector_store -> retriever -> llm_wrapper -> system_prompt -> llm_agent 

So if the user inputs a query it follows the pipeline:

query -> embedder (query_embed) -> retriever (FAISS) -> system_prompt -> llm_agent

## Project Structure 
rag-scientific-code-agent
│
├── src
│   ├── ingestion
│   │   ├── file_reader.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── (parser.py)         // not implemented yet
│   │
│   ├── retrieval
│   │   ├── vector_store.py
│   │   └── retriever.py
│   │
│   ├── prompts
│   │   └── system_prompt.py
│   │
│   ├── llm
│   │   └── llm_wrapper.py
│   │   
│   │
│   └── agent
│       └── llm_agent.py
│ 
│ 
├── test1                       // first test run
├── data
│   ├── processed
│   └── raw
│       ├── ippl 
│       └── opalx
│ 
├── configs
├── main.py
└── README.md

# Installation 
## clone repository:
$ git clone https://github.com/nobileaaron/rag-scientific-code-agent

IMPORTANT: The raw code base of ippl/opalx is not contained in the repo and needs to be added seperately.
## clone ippl framework into data/raw: 
$ git clone https://github.com/ippl-framework/ippl.git data/raw/ippl

# Running the System 
$ python main.py


