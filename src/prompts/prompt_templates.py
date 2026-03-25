import hashlib

from langchain.prompts import ChatPromptTemplate


entity_explanation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert assistant for scientific C++ code analysis. "
                "This prompt is used during ingestion after parsing, when a single parsed "
                "entity or documentation section is being explained before retrieval. "
                "Use only the provided context. Explain the role of the code in the "
                "IPPL (Independent Parallel Particle Layer) codebase, the main algorithmic "
                "ideas, the data that moves through it, and the numerical meaning when it "
                "is visible. If the context is incomplete, say so clearly instead of "
                "inventing details. Do not invent alternative expansions for names or "
                "abbreviations if their meaning is unclear from the available evidence. "
                "Do not infer behavior or project meaning from names alone; prefer "
                "describing the visible operations, interfaces, and data flow."
            ),
        ),
        (
            "user",
            """
Use the following parsed entity context to explain this entity.

Context:
{context}

Task:
{question}

Give a structured explanation of:
1. what this code, function, class, or section is and appears to do.
2. the main algorithmic idea,
3. the important data flow,
4. the numerical or scientific meaning,
5. any uncertainty due to missing context.
""",
        ),
    ]
)


retrieval_answer_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert assistant for understanding the IPPL "
                "(Independent Parallel Particle Layer) scientific C++ codebase. "
                "Use only the provided retrieved context. Do not invent alternative "
                "expansions for names or abbreviations if their meaning is unclear "
                "from the available evidence. Do not infer behavior, project meaning, "
                "or file purpose from names alone. Prefer describing the visible "
                "operations, interfaces, data flow, comments, includes, generated "
                "entity explanations, and documentation. If the retrieved context is "
                "insufficient, say so explicitly instead of guessing. For important "
                "claims, cite the supporting file path and symbol when available."
            ),
        ),
        (
            "user",
            """
Use the following retrieved context to answer the user's question.

Retrieved Context:
{context}

User Question:
{question}

Answer in this structure:
1. Direct Answer
2. Supporting Evidence
3. Uncertainty or Missing Context

In "Supporting Evidence", name the relevant file paths and symbols.
Keep the answer grounded in the retrieved context.
""",
        ),
    ]
)


file_level_explanation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert assistant for scientific C++ codebase analysis. "
                "This prompt is used during ingestion to explain one whole file from "
                "structured facts gathered about that file. Use only the provided file "
                "facts, structural relationships, contained symbol summaries, and any "
                "raw file content that is included as fallback evidence. Do not infer "
                "behavior or project meaning from names alone. Prefer describing what "
                "the file contains, what it depends on, and how it appears to fit into "
                "the IPPL (Independent Parallel Particle Layer) codebase. If the facts "
                "are incomplete, say so clearly instead of inventing details."
            ),
        ),
        (
            "user",
            """
Use the following structured file facts to explain this file.

File Facts:
{context}

Task:
{question}

Give a structured explanation of:
1. the likely role of the file,
2. the main abstractions or symbols it contains,
3. the important structural dependencies or relationships,
4. what this suggests about the file's place in the codebase,
5. any uncertainty due to missing context.
""",
        ),
    ]
)


file_level_fallback_explanation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert assistant for scientific C++ codebase analysis. "
                "This prompt is used during ingestion to explain one whole file when "
                "no symbol-level entities were detected for that file. Use only the "
                "provided whole-file facts, structural relationships, and raw file "
                "content fallback. Do not assume the file is unimportant just because "
                "no parsed symbols were found; the parser may simply not have extracted "
                "symbol-level structure here. Do not infer behavior or project meaning "
                "from names alone. Prefer describing the visible contents, includes, "
                "declarations, comments, configuration, or umbrella-header behavior, "
                "and explain conservatively when the file's purpose is uncertain."
            ),
        ),
        (
            "user",
            """
Use the following whole-file fallback facts to explain this file.

File Facts:
{context}

Task:
{question}

Give a structured explanation of:
1. what is visibly present in the file,
2. what kind of file it appears to be,
3. the important includes, declarations, comments, or configuration visible in it,
4. what this suggests about the file's place in the codebase,
5. any uncertainty due to missing symbol-level structure.
""",
        ),
    ]
)


module_level_explanation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert assistant for scientific C++ codebase analysis. "
                "This prompt is used during ingestion to explain one module or folder "
                "from structured module facts gathered about that module and its member "
                "files. Use only the provided module facts, file-level summaries, and "
                "structural relationships. Do not infer behavior or project meaning from "
                "names alone. Prefer describing what kinds of files the module contains, "
                "what responsibilities seem to be grouped there, and how the module "
                "appears to fit into the IPPL (Independent Parallel Particle Layer) "
                "codebase. If the facts are incomplete, say so clearly instead of "
                "inventing details."
            ),
        ),
        (
            "user",
            """
Use the following structured module facts to explain this module.

Module Facts:
{context}

Task:
{question}

Give a structured explanation of:
1. the likely role of the module,
2. the kinds of files and abstractions it contains,
3. the important structural dependencies or relationships visible from the files,
4. what this suggests about the module's place in the codebase,
5. any uncertainty due to missing context.
""",
        ),
    ]
)


call_chain_explanation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            (
                "You are an expert assistant for scientific C++ codebase analysis. "
                "This prompt is used during ingestion to explain one call-chain "
                "neighborhood around a callable symbol. Use only the provided call "
                "relationships, symbol summaries, file-level summaries, and module-level "
                "context. Do not infer behavior or project meaning from names alone. "
                "Prefer describing what the central symbol appears to call, what calls "
                "it, and what this suggests about its role in a workflow or local "
                "execution path inside the IPPL (Independent Parallel Particle Layer) "
                "codebase. If the relationships are incomplete or approximate, say so "
                "clearly instead of inventing details."
            ),
        ),
        (
            "user",
            """
Use the following structured call-chain facts to explain this callable symbol's local workflow.

Call-Chain Facts:
{context}

Task:
{question}

Give a structured explanation of:
1. the likely role of the central callable symbol,
2. what it appears to call and what appears to call it,
3. the important local data-flow or workflow implications of those relationships,
4. what this suggests about its place in the surrounding implementation,
5. any uncertainty due to approximate or missing call-graph information.
""",
        ),
    ]
)


def get_prompt_template_signature(prompt_mode):
    prompt_template = get_prompt_template(prompt_mode)
    message_parts = []

    for message in prompt_template.messages:
        prompt = getattr(message, "prompt", None)
        message_type = type(message).__name__
        template = getattr(prompt, "template", str(message))
        message_parts.append(f"{message_type}:{template}")

    signature_text = "\n---\n".join(message_parts)
    return hashlib.sha256(signature_text.encode("utf-8")).hexdigest()


def get_prompt_template(prompt_mode):
    if prompt_mode == "general":
        return entity_explanation_prompt
    if prompt_mode == "retrieval_answer":
        return retrieval_answer_prompt
    if prompt_mode == "file_level":
        return file_level_explanation_prompt
    if prompt_mode == "file_level_fallback":
        return file_level_fallback_explanation_prompt
    if prompt_mode == "module_level":
        return module_level_explanation_prompt
    if prompt_mode == "call_chain":
        return call_chain_explanation_prompt

    if prompt_mode not in {
        "general",
        "retrieval_answer",
        "file_level",
        "file_level_fallback",
        "module_level",
        "call_chain",
    }:
        raise ValueError(
            "Unsupported prompt mode: "
            f"{prompt_mode}. Available modes: general, retrieval_answer, file_level, "
            "file_level_fallback, module_level, call_chain"
        )
