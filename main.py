# ----- INGESTION -----
import json
import sys
from pathlib import Path

# FileReading - Imports Source Codebase & Documentation (IPPL / OPALX)
from src.ingestion.file_reader import FileReader

# Parsing - Designs a structure for code and documentation files
from src.ingestion.code.cpp_parser import create_cpp_parser
from src.ingestion.code.header_parser import create_header_parser
from src.ingestion.documentation.doc_parser import DocParser

# Chunking - Split parsed code/docs into retrieval blocks
from src.ingestion.code.cpp_function_chunker import CppFunctionChunker
from src.ingestion.code.header_chunker import HeaderChunker
from src.ingestion.documentation.doc_chunker import DocChunker
from src.ingestion.explanation_generator import EntityExplanationGenerator

# Structure Building - Builds higher-level entities for retrieval (file-level, module-level, call-chain-level)
from src.structure.file_level_entity_builder import FileLevelEntityBuilder
from src.structure.module_level_entity_builder import ModuleLevelEntityBuilder
from src.structure.call_chain_entity_builder import CallChainEntityBuilder
from src.structure.project_structure_builder import ProjectStructureBuilder

# Embedding
from src.ingestion.embedder import Embedder

# Retrieval
from src.retrieval.retriever import Retriever
from src.retrieval.vector_store import VectorStore
from src.retrieval.debugger import RetrievalDebugger

# LLM
from src.agent.llm_agent import LLMAgent
from src.llm.llm_wrapper import LLMWrapper

# Prompt
from src.prompts.prompt_templates import get_prompt_template, get_prompt_template_signature

# Paths
VECTOR_STORE_DIR = Path("embeddings/vector_store")
PROJECT_STRUCTURE_PATH = Path("embeddings/project_structure/project_structure.json")
FILE_LEVEL_ENTITIES_PATH = Path("embeddings/project_structure/file_level_entities.json")
MODULE_LEVEL_ENTITIES_PATH = Path("embeddings/project_structure/module_level_entities.json")
CALL_CHAIN_ENTITIES_PATH = Path("embeddings/project_structure/call_chain_entities.json")
SETTINGS_PATH = Path("config/runtime_settings.json")


def load_runtime_settings(settings_path):
    with Path(settings_path).open("r", encoding="utf-8") as file:
        return json.load(file)


def print_ingestion_stats(source_files, documentation_files, chunks):
    all_files = source_files + documentation_files
    unique_file_paths = {file["path"] for file in all_files}
    unique_chunk_keys = {
        (chunk["file"], chunk["function_name"], chunk["code"])
        for chunk in chunks
    }
    code_chunk_count = sum(
        1 for chunk in chunks if not str(chunk.get("return_type", "")).startswith("doc:")
    )
    doc_chunk_count = len(chunks) - code_chunk_count
    file_level_chunk_count = sum(1 for chunk in chunks if chunk.get("entity_level") == "file_level")
    module_level_chunk_count = sum(
        1 for chunk in chunks if chunk.get("entity_level") == "module_level"
    )
    call_chain_chunk_count = sum(
        1 for chunk in chunks if chunk.get("entity_level") == "call_chain_level"
    )
    explained_chunk_count = sum(
        1 for chunk in chunks if chunk.get("generated_explanation_status") == "ok"
    )
    inherited_explanation_chunk_count = sum(1 for chunk in chunks if chunk.get("generated_explanation"))

    print("\nIngestion stats:")
    print(f"Loaded source files: {len(source_files)}")
    print(f"Loaded documentation files: {len(documentation_files)}")
    print(f"Loaded files total: {len(all_files)}")
    print(f"Unique file paths: {len(unique_file_paths)}")
    print(f"Extracted chunks total: {len(chunks)}")
    print(f"Code chunks: {code_chunk_count}")
    print(f"Documentation chunks: {doc_chunk_count}")
    print(f"File-level entities: {file_level_chunk_count}")
    print(f"Module-level entities: {module_level_chunk_count}")
    print(f"Call-chain entities: {call_chain_chunk_count}")
    print(f"Chunks carrying generated explanations: {inherited_explanation_chunk_count}")
    print(f"Chunks sourced from successfully explained entities: {explained_chunk_count}")
    print(f"Unique (file, function_name, code) chunks: {len(unique_chunk_keys)}\n")


def build_code_chunks(
    code_entities,
    max_chunk_size,
):
    print("extracting code chunks...")
    cpp_chunker = CppFunctionChunker(max_chunk_size)
    header_chunker = HeaderChunker(max_chunk_size)
    cpp_functions = [
        entity for entity in code_entities if entity.get("source_type", "") == "cpp"
    ]
    header_entities = [
        entity for entity in code_entities if entity.get("source_type", "") == "header"
    ]
    cpp_chunks = cpp_chunker.chunk_functions(cpp_functions)
    header_chunks = header_chunker.chunk_entities(header_entities)

    return cpp_chunks + header_chunks


def build_documentation_chunks(
    documentation_files,
    max_chunk_size,
    explanation_generator=None,
    return_sections=False,
):
    print("parsing documentation files...")
    doc_parser = DocParser()
    doc_sections = doc_parser.parse(documentation_files)
    print(f"Parsed {len(doc_sections)} documentation sections.")

    if explanation_generator is not None:
        doc_sections = explanation_generator.enrich_entities(
            doc_sections,
            entity_level="documentation_section_level",
        )

    print("extracting documentation chunks...")
    doc_chunker = DocChunker(max_chunk_size)
    doc_chunks = doc_chunker.chunk_sections(doc_sections)
    print(f"Extracted {len(doc_chunks)} documentation chunks.")

    if return_sections:
        return doc_chunks, doc_sections

    return doc_chunks


def build_code_entities(files, parser_type, explanation_generator=None):
    cpp_files = [file for file in files if file["path"].endswith(".cpp")]
    header_files = [file for file in files if file["path"].endswith((".h", ".hpp"))]

    print(f"parsing cpp files with {parser_type} parser...")
    cpp_parser = create_cpp_parser(parser_type)
    cpp_functions = cpp_parser.extract_functions(cpp_files)
    print(f"Parsed {len(cpp_functions)} cpp functions.")

    print(f"parsing header files with {parser_type} parser...")
    header_parser = create_header_parser(parser_type)
    header_entities = header_parser.extract_entities(header_files)
    print(f"Parsed {len(header_entities)} header entities.")

    if explanation_generator is not None:
        cpp_functions = explanation_generator.enrich_entities(
            cpp_functions,
            entity_level="function_level",
        )
        header_entities = explanation_generator.enrich_entities(
            header_entities,
            entity_level="function_level",
        )

    return cpp_functions + header_entities


def resolve_parser_type(preferred_parser_type):
    try:
        create_cpp_parser(preferred_parser_type)
        create_header_parser(preferred_parser_type)
        return preferred_parser_type
    except ImportError as exc:
        fallback_parser = "regex"
        print(
            f"{preferred_parser_type} parser unavailable ({exc}). "
            f"Falling back to {fallback_parser} parser."
        )
        return fallback_parser


def build_vector_store_manifest(
    raw_data_path,
    parser_type,
    max_chunk_size,
    embedder,
    chunk_explanation_prompt_mode,
    chunk_explanation_prompt_signature,
    chunk_explanation_model,
    chunk_explanation_allowed_types,
    chunk_explanation_min_content_length,
    chunk_explanation_pilot_limit,
    file_level_prompt_mode,
    file_level_prompt_signature,
    file_level_fallback_prompt_mode,
    file_level_fallback_prompt_signature,
    file_level_model,
    file_level_entity_strategy,
    module_level_prompt_mode,
    module_level_prompt_signature,
    module_level_model,
    module_level_entity_strategy,
    call_chain_prompt_mode,
    call_chain_prompt_signature,
    call_chain_model,
    call_chain_entity_strategy,
):
    return {
        "raw_data_path": raw_data_path,
        "parser_type": parser_type,
        "max_chunk_size": max_chunk_size,
        "embedding_backend": embedder.embedding_backend,
        "embedding_model": embedder.embedding_model_name,
        "chunk_explanation_prompt_mode": chunk_explanation_prompt_mode,
        "chunk_explanation_prompt_signature": chunk_explanation_prompt_signature,
        "chunk_explanation_model": chunk_explanation_model,
        "chunk_explanation_allowed_types": list(chunk_explanation_allowed_types),
        "chunk_explanation_min_content_length": chunk_explanation_min_content_length,
        "chunk_explanation_pilot_limit": chunk_explanation_pilot_limit,
        "file_level_prompt_mode": file_level_prompt_mode,
        "file_level_prompt_signature": file_level_prompt_signature,
        "file_level_fallback_prompt_mode": file_level_fallback_prompt_mode,
        "file_level_fallback_prompt_signature": file_level_fallback_prompt_signature,
        "file_level_model": file_level_model,
        "file_level_entity_strategy": file_level_entity_strategy,
        "module_level_prompt_mode": module_level_prompt_mode,
        "module_level_prompt_signature": module_level_prompt_signature,
        "module_level_model": module_level_model,
        "module_level_entity_strategy": module_level_entity_strategy,
        "call_chain_prompt_mode": call_chain_prompt_mode,
        "call_chain_prompt_signature": call_chain_prompt_signature,
        "call_chain_model": call_chain_model,
        "call_chain_entity_strategy": call_chain_entity_strategy,
    }


def load_persisted_vector_store(vector_store_dir, expected_manifest):
    if not VectorStore.persisted_files_exist(vector_store_dir):
        return None

    vector_store, stored_manifest = VectorStore.load(vector_store_dir)
    manifest_matches = all(
        stored_manifest.get(key) == value
        for key, value in expected_manifest.items()
    )

    if not manifest_matches:
        print("Persisted vector store manifest does not match current settings. Rebuilding.")
        print("Stored manifest:")
        print(json.dumps(stored_manifest, indent=2))
        print("Expected manifest:")
        print(json.dumps(expected_manifest, indent=2))
        return None

    print(f"Loaded persisted vector store from {vector_store_dir}.")
    return vector_store


def main():
    settings = load_runtime_settings(SETTINGS_PATH)
    print(f"Loaded runtime settings from {SETTINGS_PATH}")

    # 1 LOAD SOURCE FILES FROM RAW DATA
    raw_data_path = settings["raw_data_path"]
    file_reader = FileReader(raw_data_path)

    print(f"Python interpreter: {sys.executable}")

    print("loading source files...")
    source_files = file_reader.load_source_files()
    print(f"Loaded {len(source_files)} source files.")

    print("loading documentation files...")
    documentation_files = file_reader.load_documentation_files()
    print(f"Loaded {len(documentation_files)} documentation files.")

    # 2 EXTRACT CHUNKS FROM RAW DATA
    preferred_parser_type = settings["ingestion"]["preferred_parser_type"]
    max_chunk_size = settings["ingestion"]["max_chunk_size"]
    embedding_backend = settings["embedding"]["backend"]
    ollama_embedding_model = settings["embedding"]["ollama_model"]
    sentence_transformer_model = settings["embedding"]["sentence_transformer_model"]
    answer_prompt_mode = settings["prompts"]["answer_prompt_mode"]
    chunk_explanation_prompt_mode = settings["prompts"]["chunk_explanation_prompt_mode"]
    file_level_prompt_mode = settings["prompts"]["file_level_prompt_mode"]
    file_level_fallback_prompt_mode = settings["prompts"]["file_level_fallback_prompt_mode"]
    module_level_prompt_mode = settings["prompts"]["module_level_prompt_mode"]
    call_chain_prompt_mode = settings["prompts"]["call_chain_prompt_mode"]
    chunk_explanation_model = settings["models"]["chunk_explanation_model"]
    file_level_model = settings["models"]["file_level_model"]
    module_level_model = settings["models"]["module_level_model"]
    call_chain_model = settings["models"]["call_chain_model"]
    answer_model = settings["models"]["answer_model"]
    file_level_entity_strategy = settings["strategies"]["file_level_entity_strategy"]
    module_level_entity_strategy = settings["strategies"]["module_level_entity_strategy"]
    call_chain_entity_strategy = settings["strategies"]["call_chain_entity_strategy"]
    chunk_explanation_allowed_types = settings["ingestion"]["chunk_explanation_allowed_types"]
    chunk_explanation_min_content_length = settings["ingestion"][
        "chunk_explanation_min_content_length"
    ]
    chunk_explanation_pilot_limit = settings["ingestion"]["chunk_explanation_pilot_limit"]
    retrieval_candidate_k = settings["retrieval"]["candidate_k"]
    retrieval_supplementary_k = settings["retrieval"]["supplementary_k"]
    retrieval_supplementary_candidate_k = settings["retrieval"]["supplementary_candidate_k"]
    retrieval_debug_default = settings["retrieval"]["debug_enabled_by_default"]
    parser_type = resolve_parser_type(preferred_parser_type)
    prompt_template = get_prompt_template(answer_prompt_mode)
    chunk_explanation_prompt_signature = get_prompt_template_signature(
        chunk_explanation_prompt_mode
    )
    file_level_prompt_signature = get_prompt_template_signature(file_level_prompt_mode)
    file_level_fallback_prompt_signature = get_prompt_template_signature(
        file_level_fallback_prompt_mode
    )
    module_level_prompt_signature = get_prompt_template_signature(module_level_prompt_mode)
    call_chain_prompt_signature = get_prompt_template_signature(call_chain_prompt_mode)
    embedder = Embedder(
        backend=embedding_backend,
        ollama_model=ollama_embedding_model,
        transformer_model_name=sentence_transformer_model,
    )
    vector_store_manifest = build_vector_store_manifest(
        raw_data_path=raw_data_path,
        parser_type=parser_type,
        max_chunk_size=max_chunk_size,
        embedder=embedder,
        chunk_explanation_prompt_mode=chunk_explanation_prompt_mode,
        chunk_explanation_prompt_signature=chunk_explanation_prompt_signature,
        chunk_explanation_model=chunk_explanation_model,
        chunk_explanation_allowed_types=chunk_explanation_allowed_types,
        chunk_explanation_min_content_length=chunk_explanation_min_content_length,
        chunk_explanation_pilot_limit=chunk_explanation_pilot_limit,
        file_level_prompt_mode=file_level_prompt_mode,
        file_level_prompt_signature=file_level_prompt_signature,
        file_level_fallback_prompt_mode=file_level_fallback_prompt_mode,
        file_level_fallback_prompt_signature=file_level_fallback_prompt_signature,
        file_level_model=file_level_model,
        file_level_entity_strategy=file_level_entity_strategy,
        module_level_prompt_mode=module_level_prompt_mode,
        module_level_prompt_signature=module_level_prompt_signature,
        module_level_model=module_level_model,
        module_level_entity_strategy=module_level_entity_strategy,
        call_chain_prompt_mode=call_chain_prompt_mode,
        call_chain_prompt_signature=call_chain_prompt_signature,
        call_chain_model=call_chain_model,
        call_chain_entity_strategy=call_chain_entity_strategy,
    )

    vector_store = load_persisted_vector_store(VECTOR_STORE_DIR, vector_store_manifest)
    chunks = []

    explanation_generator = None
    if vector_store is None:
        explanation_llm = LLMWrapper(model=chunk_explanation_model)
        explanation_generator = EntityExplanationGenerator(
            explanation_llm,
            prompt_mode=chunk_explanation_prompt_mode,
            allowed_chunk_types=chunk_explanation_allowed_types,
            min_content_length=chunk_explanation_min_content_length,
            pilot_limit=chunk_explanation_pilot_limit,
        )
        print("\nChunk explanation configuration:")
        print(f"Prompt mode: {chunk_explanation_prompt_mode}")
        print(f"Prompt signature: {chunk_explanation_prompt_signature}")
        print(f"Model: {chunk_explanation_model}")
        print(f"Allowed chunk types: {', '.join(chunk_explanation_allowed_types)}")
        print(f"Minimum content length: {chunk_explanation_min_content_length}")
        print(f"Pilot limit: {chunk_explanation_pilot_limit}\n")

    print("building code entities...")
    code_entities = build_code_entities(
        source_files,
        parser_type,
        explanation_generator=explanation_generator,
    )

    print("building project structure...")
    structure_builder = ProjectStructureBuilder(raw_data_path)
    project_structure = structure_builder.build(
        source_files,
        code_entities=code_entities,
        documentation_files=documentation_files,
    )
    structure_builder.save(project_structure, PROJECT_STRUCTURE_PATH)
    structure_builder.print_summary(project_structure)
    print(f"Saved project structure to {PROJECT_STRUCTURE_PATH}.\n")

    if vector_store is None:
        code_chunks = build_code_chunks(
            code_entities,
            max_chunk_size,
        )
        doc_chunks, _ = build_documentation_chunks(
            documentation_files,
            max_chunk_size,
            explanation_generator=explanation_generator,
            return_sections=True,
        )
        file_level_builder = FileLevelEntityBuilder(
            LLMWrapper(model=file_level_model),
            prompt_mode=file_level_prompt_mode,
            fallback_prompt_mode=file_level_fallback_prompt_mode,
        )
        file_contents = {
            file_data["path"]: file_data["content"]
            for file_data in source_files + documentation_files
        }
        print("building file-level entities...")
        print(f"File-level prompt mode: {file_level_prompt_mode}")
        print(f"File-level prompt signature: {file_level_prompt_signature}")
        print(f"File-level fallback prompt mode: {file_level_fallback_prompt_mode}")
        print(f"File-level fallback prompt signature: {file_level_fallback_prompt_signature}")
        print(f"File-level model: {file_level_model}")
        print(f"File-level entity strategy: {file_level_entity_strategy}")
        file_level_entities = file_level_builder.build(
            project_structure,
            code_entities,
            file_contents,
        )
        file_level_builder.save(file_level_entities, FILE_LEVEL_ENTITIES_PATH)
        print(f"Built {len(file_level_entities)} file-level entities.")
        print(f"Saved file-level entities to {FILE_LEVEL_ENTITIES_PATH}.\n")

        module_level_builder = ModuleLevelEntityBuilder(
            LLMWrapper(model=module_level_model),
            prompt_mode=module_level_prompt_mode,
        )
        print("building module-level entities...")
        print(f"Module-level prompt mode: {module_level_prompt_mode}")
        print(f"Module-level prompt signature: {module_level_prompt_signature}")
        print(f"Module-level model: {module_level_model}")
        print(f"Module-level entity strategy: {module_level_entity_strategy}")
        module_level_entities = module_level_builder.build(
            project_structure,
            file_level_entities,
        )
        module_level_builder.save(module_level_entities, MODULE_LEVEL_ENTITIES_PATH)
        print(f"Built {len(module_level_entities)} module-level entities.")
        print(f"Saved module-level entities to {MODULE_LEVEL_ENTITIES_PATH}.\n")

        call_chain_builder = CallChainEntityBuilder(
            LLMWrapper(model=call_chain_model),
            prompt_mode=call_chain_prompt_mode,
        )
        print("building call-chain entities...")
        print(f"Call-chain prompt mode: {call_chain_prompt_mode}")
        print(f"Call-chain prompt signature: {call_chain_prompt_signature}")
        print(f"Call-chain model: {call_chain_model}")
        print(f"Call-chain entity strategy: {call_chain_entity_strategy}")
        call_chain_entities = call_chain_builder.build(
            project_structure,
            code_entities,
            file_level_entities,
            module_level_entities,
        )
        call_chain_builder.save(call_chain_entities, CALL_CHAIN_ENTITIES_PATH)
        print(f"Built {len(call_chain_entities)} call-chain entities.")
        print(f"Saved call-chain entities to {CALL_CHAIN_ENTITIES_PATH}.\n")

        chunks = (
            code_chunks
            + doc_chunks
            + file_level_entities
            + module_level_entities
            + call_chain_entities
        )
        explanation_generator.print_summary()

        print(f"Extracted {len(chunks)} total chunks.")
        print_ingestion_stats(source_files, documentation_files, chunks)

        if not chunks:
            print("No chunks were extracted. Check the data directory and supported file types.")
            return

        # 3 EMBED CHUNKS INTO VECTORS
        embeddings = embedder.embed_chunks(chunks)

        # 4 STORE EMBEDDINGS IN VECTOR_STORE
        print("building vector store...")
        vector_store = VectorStore(len(embeddings[0]))
        vector_store.add(embeddings, chunks)
        vector_store.save(VECTOR_STORE_DIR, vector_store_manifest)
        print(f"Saved vector store to {VECTOR_STORE_DIR}.")
    else:
        print(
            f"Using persisted vector store with {len(vector_store.metadata)} chunks "
            f"from {VECTOR_STORE_DIR}."
        )

    # 5 INITIALIZING RETRIEVER
    print("initializing retriever...")
    retriever = Retriever(
        embedder,
        vector_store,
        candidate_k=retrieval_candidate_k,
        supplementary_k=retrieval_supplementary_k,
        supplementary_candidate_k=retrieval_supplementary_candidate_k,
    )

    # 6 INITIALIZING LLM
    llm = LLMWrapper(model=answer_model)

    # 7 INITIALIZING AGENT

    retrieval_debugger = RetrievalDebugger(enabled=retrieval_debug_default)
    agent = LLMAgent(retriever, llm, prompt_template, retrieval_debugger)

    print("\nSystem ready. Ask questions about the code and documentation.")
    print(f"Answer prompt mode: {answer_prompt_mode}")
    print(f"Chunk explanation prompt mode: {chunk_explanation_prompt_mode}")
    print("Use ':debug on' or ':debug off' to toggle retrieval debugging.\n")

    while True:
        query = input("Query: ")

        if query.lower() in ["exit", "quit"]:
            break

        if query.lower() == ":debug on":
            retrieval_debugger.enabled = True
            print("Retrieval debugging enabled.\n")
            continue

        if query.lower() == ":debug off":
            retrieval_debugger.enabled = False
            print("Retrieval debugging disabled.\n")
            continue

        answer = agent.answer(query)

        print("\nAnswer:\n")
        print(answer)
        print("\n-----------------------------\n")


if __name__ == "__main__":
    main()
