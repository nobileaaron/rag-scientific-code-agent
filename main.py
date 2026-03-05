#Ingestion
from src.ingestion.file_reader import load_coding_files
from src.ingestion.chunker import Chunker
from src.ingestion.embedder import Embedder

#Retrieval
from src.retrieval.retriever import Retriever
from src.retrieval.vector_store import VectorStore

#LLM
from src.agent.llm_agent import LLMAgent
from src.llm.llm_wrapper import LLMWrapper

#prompt
from src.prompts.system_prompt import code_explanation_prompt

def main():
    # 1 LOAD SOURCE FILES FROM RAW DATA

    print("loading coding files...")
    files = load_coding_files("data/raw/ippl", [".cpp", ".hpp", ".h"])
    print(f"Loaded {len(files)} files.")

    # 2 EXTRACT CHUNKS (FUNCTIONS) RAW DATA

    # chunks will be seperated into:
    # "stored file path " = chunks["file"]
    # "function name"     = chunks["function_name"]
    # "entire code"       = chunks["code"]

    print("extracting chunks...")
    chunker = Chunker()
    chunks = chunker.extract_functions(files)
    print(f"Extracted {len(chunks)} function chunks.")

    # 3 EMBED CHUNKS INTO VECTORS

    # using ollama_embed

    embedder = Embedder()
    embeddings = embedder.ollama_embed(chunks)
    
    # 4 STORE EMBEDDINGS IN VECTOR_STORE
    print("building vector store...")
    vector_store = VectorStore(len(embeddings[0]))
    vector_store.add(embeddings, chunks)

    # 5 INITIALIZING RETRIEVER
    print("initializing retriever...")
    retriever = Retriever(embedder, vector_store)

    # 7 INITIALIZING LLM - WRAPPER -> (talks to agent) -> choose llm model
    llm = LLMWrapper(model="deepseek-coder")

    # 8 INITIALIZING AGENT 
    # set retriever -> how are embeddings retrieved
    # llm set 
    # choose prompt template (different versions inside "prompts")

    agent = LLMAgent(retriever, llm, code_explanation_prompt)

    print("\nSystem ready. Ask questions about the code.\n")

    while True:

        query = input("Query: ")

        if query.lower() in ["exit", "quit"]:
            break

        answer = agent.answer(query)

        print("\nAnswer:\n")
        print(answer)
        print("\n-----------------------------\n")


if __name__ == "__main__":
    main()