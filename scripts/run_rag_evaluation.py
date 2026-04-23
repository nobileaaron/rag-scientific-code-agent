"""Run the IPPL RAG pipeline over a set of evaluation questions.

Reuses the ingestion/embedding/retrieval setup from ``main.py`` to build the
agent, then iterates the configured questions JSON and dumps each answer
(plus metadata about the models used in this run) into a single results
JSON under ``docs/evaluations/answers/``.

Intended to be run via ``eval_job.sh`` on gwendolen, but can also be run
locally with ``RAG_ALLOW_REBUILD=1``.

Environment variables:
    EVAL_QUESTIONS_PATH  path to the questions JSON
                         (default: docs/evaluations/eval_questions_v1.json)
    EVAL_OUTPUT_PATH     path to the output JSON
                         (default: docs/evaluations/answers/eval_<timestamp>.json)
    EVAL_RUN_LABEL       optional short label for this run
                         (echoed into run_metadata for later comparison)
"""

import json
import os
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Make the repo root importable when launched from anywhere.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Reuse as much of main.py as possible so the pipeline being evaluated is
# exactly the one the user runs interactively.
import main as rag_main  # noqa: E402
from src.agent.llm_agent import LLMAgent  # noqa: E402
from src.ingestion.embedder import Embedder  # noqa: E402
from src.llm.llm_wrapper import LLMWrapper, model_manifest_key  # noqa: E402
from src.prompts.prompt_templates import (  # noqa: E402
    get_prompt_template,
    get_prompt_template_signature,
)
from src.retrieval.debugger import RetrievalDebugger  # noqa: E402
from src.retrieval.retriever import Retriever  # noqa: E402


DEFAULT_QUESTIONS_PATH = REPO_ROOT / "docs" / "evaluations" / "eval_questions_v1.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "evaluations" / "answers"


def resolve_questions_path():
    override = os.environ.get("EVAL_QUESTIONS_PATH")
    if override:
        return Path(override)
    return DEFAULT_QUESTIONS_PATH


def resolve_output_path():
    override = os.environ.get("EVAL_OUTPUT_PATH")
    if override:
        return Path(override)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_OUTPUT_DIR / f"eval_{timestamp}.json"


def build_models_section(settings):
    """Snapshot every configured model with a normalized manifest key.

    The manifest key (``provider:name``) is the same one the vector-store
    manifest uses, so evaluating runs can be compared apples-to-apples by
    matching these keys.
    """
    models_in = settings.get("models", {}) or {}
    resolved = {}
    for role, entry in models_in.items():
        resolved[role] = {
            "raw": entry,
            "manifest_key": model_manifest_key(entry),
        }
    return resolved


def build_agent_from_settings():
    """Assemble the same LLMAgent main.py builds, without the REPL loop.

    This mirrors ``main.main()`` but stops after the agent is ready and
    returns the agent plus a snapshot of the settings and vector store for
    logging.
    """
    settings = rag_main.load_runtime_settings(rag_main.SETTINGS_PATH)
    print(f"Loaded runtime settings from {rag_main.SETTINGS_PATH}")

    raw_data_path = settings["raw_data_path"]
    file_reader = rag_main.FileReader(raw_data_path)
    print("loading source files...")
    source_files = file_reader.load_source_files()
    print(f"Loaded {len(source_files)} source files.")
    print("loading documentation files...")
    documentation_files = file_reader.load_documentation_files()
    print(f"Loaded {len(documentation_files)} documentation files.")

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

    parser_type = rag_main.resolve_parser_type(preferred_parser_type)
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
    vector_store_manifest = rag_main.build_vector_store_manifest(
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

    # We deliberately do not rebuild the vector store here. The evaluation
    # script expects that job.sh (or an interactive pre-run) has already
    # produced it. Requiring a persisted store keeps the evaluation loop
    # focused on answering, not ingestion.
    vector_store = rag_main.load_persisted_vector_store(
        rag_main.VECTOR_STORE_DIR, vector_store_manifest
    )
    if vector_store is None:
        raise SystemExit(
            "No usable persisted vector store for this settings manifest. "
            "Run `sbatch job.sh` (or `RAG_ALLOW_REBUILD=1 python main.py`) first "
            "to build artifacts, then re-run the evaluation."
        )

    print(
        f"Using persisted vector store with {len(vector_store.metadata)} chunks "
        f"from {rag_main.VECTOR_STORE_DIR}."
    )

    retriever = Retriever(
        embedder,
        vector_store,
        candidate_k=retrieval_candidate_k,
        supplementary_k=retrieval_supplementary_k,
        supplementary_candidate_k=retrieval_supplementary_candidate_k,
    )
    llm = LLMWrapper(model=answer_model)
    retrieval_debugger = RetrievalDebugger(enabled=retrieval_debug_default)
    agent = LLMAgent(
        retriever,
        llm,
        prompt_template,
        retrieval_debugger,
        prompt_mode=answer_prompt_mode,
    )

    return {
        "agent": agent,
        "settings": settings,
        "vector_store_manifest": vector_store_manifest,
        "vector_store_chunk_count": len(vector_store.metadata),
        "parser_type": parser_type,
        "answer_prompt_signature": get_prompt_template_signature(answer_prompt_mode),
    }


def run_evaluation():
    questions_path = resolve_questions_path()
    output_path = resolve_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with questions_path.open("r", encoding="utf-8") as f:
        questions_doc = json.load(f)
    questions = questions_doc.get("questions", [])
    if not questions:
        raise SystemExit(f"No questions found in {questions_path}.")
    print(f"Loaded {len(questions)} evaluation questions from {questions_path}.")

    build_result = build_agent_from_settings()
    agent = build_result["agent"]
    settings = build_result["settings"]

    run_started_at = datetime.now(timezone.utc).isoformat()
    run_metadata = {
        "run_label": os.environ.get("EVAL_RUN_LABEL", ""),
        "run_started_at_utc": run_started_at,
        "hostname": socket.gethostname(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", ""),
        "slurm_partition": os.environ.get("SLURM_JOB_PARTITION", ""),
        "python_executable": sys.executable,
        "questions_source": str(questions_path),
        "questions_version": questions_doc.get("version", ""),
        "vector_store_chunk_count": build_result["vector_store_chunk_count"],
        "parser_type": build_result["parser_type"],
        "answer_prompt_mode": settings["prompts"]["answer_prompt_mode"],
        "answer_prompt_signature": build_result["answer_prompt_signature"],
    }

    models_section = build_models_section(settings)
    print("Configured models for this run:")
    for role, info in models_section.items():
        print(f"  {role}: {info['manifest_key']}")

    answers = []
    failures = 0
    for index, entry in enumerate(questions, start=1):
        question_id = entry.get("id", f"q{index:03d}")
        category = entry.get("category", "uncategorized")
        question_text = entry.get("question", "")
        if not question_text:
            print(f"[{index}/{len(questions)}] {question_id} (skipped: empty question)")
            continue

        print(f"[{index}/{len(questions)}] {question_id} ({category})")
        start = time.monotonic()
        try:
            answer = agent.answer(question_text)
            error = None
        except Exception as exc:  # noqa: BLE001 - evaluation must keep going
            failures += 1
            answer = ""
            error = {
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
            print(f"  -> FAILED: {exc}")
        elapsed = time.monotonic() - start

        answers.append(
            {
                "id": question_id,
                "category": category,
                "question": question_text,
                "answer": answer,
                "latency_seconds": elapsed,
                "error": error,
            }
        )

        # Flush progress to disk after each question so a cluster preemption
        # does not cost us all completed answers.
        _write_results(
            output_path=output_path,
            run_metadata=run_metadata,
            models_section=models_section,
            settings=settings,
            vector_store_manifest=build_result["vector_store_manifest"],
            answers=answers,
            run_finished=False,
        )

    run_metadata["run_finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    run_metadata["answer_count"] = len(answers)
    run_metadata["failure_count"] = failures

    _write_results(
        output_path=output_path,
        run_metadata=run_metadata,
        models_section=models_section,
        settings=settings,
        vector_store_manifest=build_result["vector_store_manifest"],
        answers=answers,
        run_finished=True,
    )
    print(
        f"\nWrote {len(answers)} answers ({failures} failures) to {output_path}."
    )


def _write_results(
    output_path,
    run_metadata,
    models_section,
    settings,
    vector_store_manifest,
    answers,
    run_finished,
):
    payload = {
        "schema": "rag-ippl-eval/v1",
        "run_complete": run_finished,
        "run_metadata": run_metadata,
        "models": models_section,
        "settings_snapshot": settings,
        "vector_store_manifest": vector_store_manifest,
        "answers": answers,
    }
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    run_evaluation()
