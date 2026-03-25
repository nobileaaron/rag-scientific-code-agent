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
git clone https://github.com/nobileaaron/rag-scientific-code-agent

IMPORTANT: The raw code base of ippl/opalx is not contained in the repo and needs to be added seperately.
## clone ippl framework into data/raw: 
git clone https://github.com/ippl-framework/ippl.git data/raw/ippl

# Running the System
Use the project virtual environment as the default interpreter:

```bash
/Users/aaron/semester_project/.venv/bin/python main.py
```

You can also use the repo-local launcher:

```bash
./run_main.sh
```

The project expects the `.venv` interpreter because structural analysis depends on
tree-sitter packages installed there.





# Debugging (implemented in debugger.py)
Turn Debugging Mode on/off by typing ":debug on" or ":debug off" in query.

Debugger shows, which chunks are chosen by the LLM and why.

1. Candidate Pool Size - How many Chunks were considered before top results were chosen
2. Exact Filenames detected - Which file names are in the Query & data/raw
3. Combined - final total score used for ranking 
4. Semantic - How well does the chunk match query by embedding similarity
5. Metadata - How much the chunk matched through metadata - (filename, symbol name, source type or query tokens)

# Ingestion

1. File Reader (file_reader.py)
differentiates between two type of files:
- code reading              -> reading all C++ Source Code files [".cpp", ".hpp", ".h"]
- documentation reading     -> reading all documentation files   [".md", ".rst", ".txt"]    


2. Parsing (cpp_parser.py, header_parser.py, doc_parser.py)
- cpp_parser.py             -> parses cpp files from source code

The "Cpp-Parser" implements a structured representation of ".cpp" code. For this the system can use two different methods:

-Regex                      ->  System finds a function starting language pattern and recognizes it f.e. int PoissonSolver(int x, ...){.....} from the starting point the system looks for the last semicolon and stops there. (This Method often times leads to mystakes, since it doesn't respect the actual syntax of the cpp code and is more based on text patterns.)


-TreeSitter (recommended)   -> parser generator and incremental parsing system for source code, builds a system for source code. 

TreeSitter uses following attributes for the code structure:
----file-related fields----
    1.  path - Full path to the file
            example: data/raw/ippl/src/FFT/FFTSolver.cpp
    2.  file - same file path, kept for compatibility with the rest of the pipeline
    3.  file_name - extracts only the filename
            example: FFTSolver.cpp
    4.  base_name - filename without extension - useful to later connect .cpp with related .hppfile
            example: FFTSolver

----source classification fields----
    5.  language - programming language of the parsed code
        here: cpp (C++ the language)
    6.  source_type - what kind of source the information came from
            examples: cpp / hpp / h 
    7.  entity_type - what kind of parsed this is this? - gives semantic label for the kind of structured object the parser found. 
            examples: function definition, method declaration, class, doc section.
    8.  chunk_type - 

----symbol relationship fields---- 
"How is a parsed code element related to other code elements?"
    9.  symbol_name - gives the main name of the parsed entity
            -> .cpp function: *function name
            -> header method: *method name 
            -> class/struct:  *class/struct name
            -> doc chunk:     *section title
    10. function_name - kept because pipeline expected this field from older versions
    11. parent_symbol
    12. class_name - gives the class this function belongs to (if available)

----function signature fields----
    13. return_type - returns type of the function
            example: int, double, ...
    14. parameters - parameter list of the function without parentheses
            example: int, double, ...

----location/sturcture fields----
    15. section_path - structural location information?
    16. namespace_path - 

----chunk bookkeeping----
    17. chunk_index - which chunk number is this within the parsed entity. (overwritten by chunker later)
    18. total_chunks - how many chunks does the parsed entity contain. (overwritten by chunker later.)

----content-----
    19. code - takes the full definition text of the parsed entity 
        






