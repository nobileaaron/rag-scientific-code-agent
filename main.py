# ----- INGESTION -----
import json
import os
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
from src.ingestion.explanation_snapshots import (
    build_explanation_snapshot_key,
    restore_saved_explanation,
)

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

# Debugging
from src.retrieval.debugger import RetrievalDebugger

# LLM
from src.agent.llm_agent import LLMAgent
from src.llm.llm_wrapper import LLMWrapper

# Prompt
from src.prompts.prompt_templates import (
    get_compatible_prompt_template_signatures,
    get_prompt_template,
    get_prompt_template_signature,
)

# Paths
VECTOR_STORE_DIR = Path("embeddings/vector_store")
PROJECT_STRUCTURE_PATH = Path("embeddings/project_structure/project_structure.json")
FILE_LEVEL_ENTITIES_PATH = Path("embeddings/project_structure/file_level_entities.json")
MODULE_LEVEL_ENTITIES_PATH = Path("embeddings/project_structure/module_level_entities.json")
CALL_CHAIN_ENTITIES_PATH = Path("embeddings/project_structure/call_chain_entities.json")
EXPLANATIONS_DIR = Path("embeddings/explanations")
FUNCTION_LEVEL_EXPLANATIONS_PATH = EXPLANATIONS_DIR / "function_level_explanations.json"
DOCUMENTATION_SECTION_EXPLANATIONS_PATH = (
    EXPLANATIONS_DIR / "documentation_section_level_explanations.json"
)
FILE_LEVEL_EXPLANATIONS_PATH = EXPLANATIONS_DIR / "file_level_explanations.json"
MODULE_LEVEL_EXPLANATIONS_PATH = EXPLANATIONS_DIR / "module_level_explanations.json"
CALL_CHAIN_LEVEL_EXPLANATIONS_PATH = EXPLANATIONS_DIR / "call_chain_level_explanations.json"
SETTINGS_PATH = Path("config/runtime_settings.json")


def load_runtime_settings(settings_path):
    with Path(settings_path).open("r", encoding="utf-8") as file:
        return json.load(file)


def save_explanation_snapshots(entities, output_path, entity_level):
    snapshot_records = []
    for entity in entities:
        if not entity.get("generated_explanation_status"):
            continue

        snapshot_records.append(
            {
                "entity_key": build_explanation_snapshot_key(entity),
                "entity_id": entity.get("entity_id", ""),
                "entity_level": entity_level,
                "path": entity.get("path", entity.get("file", "")),
                "file_name": entity.get("file_name", ""),
                "symbol_name": entity.get(
                    "symbol_name",
                    entity.get("function_name", entity.get("section_title", "")),
                ),
                "parent_symbol": entity.get("parent_symbol", entity.get("class_name", "")),
                "chunk_type": entity.get("chunk_type", entity.get("entity_type", "")),
                "source_type": entity.get("source_type", entity.get("doc_type", "")),
                "module_key": entity.get("module_key", ""),
                "generated_explanation": entity.get("generated_explanation", ""),
                "generated_explanation_status": entity.get("generated_explanation_status", ""),
                "generated_explanation_error": entity.get("generated_explanation_error", ""),
                "generated_explanation_prompt_mode": entity.get(
                    "generated_explanation_prompt_mode", ""
                ),
                "generated_explanation_model": entity.get("generated_explanation_model", ""),
            }
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(snapshot_records, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(f"Saved {len(snapshot_records)} {entity_level} explanation snapshots to {output_path}.")


def load_explanation_snapshots(snapshot_path):
    snapshot_path = Path(snapshot_path)
    if not snapshot_path.exists():
        return {}

    with snapshot_path.open("r", encoding="utf-8") as file:
        records = json.load(file)

    snapshot_map = {
        record["entity_key"]: record
        for record in records
        if record.get("generated_explanation_status") == "ok"
        and record.get("generated_explanation", "").strip()
    }
    print(f"Loaded {len(snapshot_map)} explanation snapshots from {snapshot_path}.")
    return snapshot_map


def apply_saved_explanations(entities, snapshot_records, entity_level):
    if not snapshot_records:
        return entities

    restored_count = 0
    for entity in entities:
        if restore_saved_explanation(entity, snapshot_records, entity_level):
            restored_count += 1

    print(f"Restored {restored_count} {entity_level} explanations from saved snapshots.")
    return entities


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
    saved_explanations=None,
    return_sections=False,
):
    print("parsing documentation files...")
    doc_parser = DocParser()
    doc_sections = doc_parser.parse(documentation_files)
    print(f"Parsed {len(doc_sections)} documentation sections.")

    if saved_explanations:
        doc_sections = apply_saved_explanations(
            doc_sections,
            saved_explanations,
            entity_level="documentation_section_level",
        )

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


def build_code_entities(
    files,
    parser_type,
    explanation_generator=None,
    saved_explanations=None,
):
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

    if saved_explanations:
        cpp_functions = apply_saved_explanations(
            cpp_functions,
            saved_explanations,
            entity_level="function_level",
        )
        header_entities = apply_saved_explanations(
            header_entities,
            saved_explanations,
            entity_level="function_level",
        )

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
        "chunker_version": "2.0-leading-comment-prepended",
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


def vector_store_rebuild_allowed():
    return os.environ.get("RAG_ALLOW_REBUILD", "0") == "1"


def load_persisted_vector_store(vector_store_dir, expected_manifest):
    rebuild_allowed = vector_store_rebuild_allowed()

    if not VectorStore.persisted_files_exist(vector_store_dir):
        if rebuild_allowed:
            return None
        raise SystemExit(
            f"No persisted vector store found at {vector_store_dir}. "
            "Rebuilding is only enabled when running via `sbatch job.sh` "
            "(set RAG_ALLOW_REBUILD=1 to build from `python main.py`)."
        )

    vector_store, stored_manifest = VectorStore.load(vector_store_dir)
    prompt_signature_keys = {
        "chunk_explanation_prompt_signature": "chunk_explanation_prompt_mode",
        "file_level_prompt_signature": "file_level_prompt_mode",
        "file_level_fallback_prompt_signature": "file_level_fallback_prompt_mode",
        "module_level_prompt_signature": "module_level_prompt_mode",
        "call_chain_prompt_signature": "call_chain_prompt_mode",
    }

    manifest_matches = True
    for key, value in expected_manifest.items():
        stored_value = stored_manifest.get(key)
        prompt_mode_key = prompt_signature_keys.get(key)
        if prompt_mode_key is not None:
            compatible_signatures = get_compatible_prompt_template_signatures(
                expected_manifest[prompt_mode_key]
            )
            if stored_value in compatible_signatures:
                continue

        if stored_value != value:
            manifest_matches = False
            break

    if not manifest_matches:
        print("Stored manifest:")
        print(json.dumps(stored_manifest, indent=2))
        print("Expected manifest:")
        print(json.dumps(expected_manifest, indent=2))
        if rebuild_allowed:
            print("Persisted vector store manifest does not match current settings. Rebuilding.")
            return None
        print(
            "Persisted vector store manifest does not match current settings, "
            "but rebuilding is only enabled when running via `sbatch job.sh`. "
            "Reusing the persisted store as-is."
        )

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
    function_level_snapshots = {}
    documentation_section_snapshots = {}
    file_level_snapshots = {}
    module_level_snapshots = {}
    call_chain_level_snapshots = {}
    if vector_store is None:
        function_level_snapshots = load_explanation_snapshots(FUNCTION_LEVEL_EXPLANATIONS_PATH)
        documentation_section_snapshots = load_explanation_snapshots(
            DOCUMENTATION_SECTION_EXPLANATIONS_PATH
        )
        file_level_snapshots = load_explanation_snapshots(FILE_LEVEL_EXPLANATIONS_PATH)
        module_level_snapshots = load_explanation_snapshots(MODULE_LEVEL_EXPLANATIONS_PATH)
        call_chain_level_snapshots = load_explanation_snapshots(
            CALL_CHAIN_LEVEL_EXPLANATIONS_PATH
        )
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
        saved_explanations=function_level_snapshots,
    )
    if vector_store is None:
        save_explanation_snapshots(
            code_entities,
            FUNCTION_LEVEL_EXPLANATIONS_PATH,
            "function_level",
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
        doc_chunks, doc_sections = build_documentation_chunks(
            documentation_files,
            max_chunk_size,
            explanation_generator=explanation_generator,
            saved_explanations=documentation_section_snapshots,
            return_sections=True,
        )
        save_explanation_snapshots(
            doc_sections,
            DOCUMENTATION_SECTION_EXPLANATIONS_PATH,
            "documentation_section_level",
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
            saved_explanations=file_level_snapshots,
        )
        file_level_builder.save(file_level_entities, FILE_LEVEL_ENTITIES_PATH)
        save_explanation_snapshots(
            file_level_entities,
            FILE_LEVEL_EXPLANATIONS_PATH,
            "file_level",
        )
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
            saved_explanations=module_level_snapshots,
        )
        module_level_builder.save(module_level_entities, MODULE_LEVEL_ENTITIES_PATH)
        save_explanation_snapshots(
            module_level_entities,
            MODULE_LEVEL_EXPLANATIONS_PATH,
            "module_level",
        )
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
            saved_explanations=call_chain_level_snapshots,
        )
        call_chain_builder.save(call_chain_entities, CALL_CHAIN_ENTITIES_PATH)
        save_explanation_snapshots(
            call_chain_entities,
            CALL_CHAIN_LEVEL_EXPLANATIONS_PATH,
            "call_chain_level",
        )
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
    agent = LLMAgent(
        retriever,
        llm,
        prompt_template,
        retrieval_debugger,
        prompt_mode=answer_prompt_mode,
    )

    print("\nSystem ready. Ask questions about the code and documentation.")
    print(f"Answer prompt mode: {answer_prompt_mode}")
    print(f"Chunk explanation prompt mode: {chunk_explanation_prompt_mode}")
    print("Use ':debug on' or ':debug off' to toggle retrieval and prompt debugging.\n")

    while True:
        try:
            query = input("Query: ")
        except EOFError:
            print("\nNo interactive stdin available; exiting after artifact build.")
            break

        if query.lower() in ["exit", "quit"]:
            break

        if query.lower() == ":debug on":
            retrieval_debugger.enabled = True
            print("Retrieval and prompt debugging enabled.\n")
            continue

        if query.lower() == ":debug off":
            retrieval_debugger.enabled = False
            print("Retrieval and prompt debugging disabled.\n")
            continue

        answer = agent.answer(query)

        print("\nAnswer:\n")
        print(answer)
        print("\n-----------------------------\n")


if __name__ == "__main__":
    main()
