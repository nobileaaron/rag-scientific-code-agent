import hashlib

try:
    from langchain.prompts import ChatPromptTemplate
except ImportError:
    try:
        from langchain.prompts.chat import ChatPromptTemplate
    except ImportError:
        class _SimplePrompt:
            def __init__(self, template):
                self.template = template

        class _SimpleMessage:
            def __init__(self, role, template):
                self.role = role
                self.prompt = _SimplePrompt(template)

        class ChatPromptTemplate:
            def __init__(self, messages):
                self.messages = [_SimpleMessage(role, template) for role, template in messages]

            @classmethod
            def from_messages(cls, messages):
                return cls(messages)

            def format(self, **kwargs):
                rendered_parts = []
                for message in self.messages:
                    rendered_parts.append(
                        f"{message.role.upper()}:\n{message.prompt.template.format(**kwargs)}"
                    )
                return "\n\n".join(rendered_parts)


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
                "You are an expert assistant for understanding the IPPL C++ codebase."
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
4. Explanation of Reasoning

In "Supporting Evidence", name the relevant file paths and symbols.
Keep the answer grounded in the retrieved context.

In "Explanation of Reasoning", explain exactly what retrieved information supports each part of your answer.
List the specific pieces of evidence that led you to each conclusion, and how they connect to the question.
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
    signature_text = _build_prompt_signature_text(prompt_template)
    return hashlib.sha256(signature_text.encode("utf-8")).hexdigest()


def get_compatible_prompt_template_signatures(prompt_mode):
    prompt_template = get_prompt_template(prompt_mode)
    signatures = {
        hashlib.sha256(_build_prompt_signature_text(prompt_template).encode("utf-8")).hexdigest(),
        hashlib.sha256(
            _build_legacy_prompt_signature_text(
                prompt_template,
                system_message_type="SystemMessagePromptTemplate",
                user_message_type="HumanMessagePromptTemplate",
            ).encode("utf-8")
        ).hexdigest(),
        hashlib.sha256(
            _build_legacy_prompt_signature_text(
                prompt_template,
                system_message_type="_SimpleMessage",
                user_message_type="_SimpleMessage",
            ).encode("utf-8")
        ).hexdigest(),
    }
    return signatures


def _build_prompt_signature_text(prompt_template):
    message_parts = []
    for message in prompt_template.messages:
        template = _extract_message_template(message)
        role = _extract_message_role(message)
        message_parts.append(f"{role}:{template}")
    return "\n---\n".join(message_parts)


def _build_legacy_prompt_signature_text(
    prompt_template,
    system_message_type,
    user_message_type,
):
    message_parts = []
    for message in prompt_template.messages:
        template = _extract_message_template(message)
        role = _extract_message_role(message)
        message_type = system_message_type if role == "system" else user_message_type
        message_parts.append(f"{message_type}:{template}")
    return "\n---\n".join(message_parts)


def _extract_message_template(message):
    prompt = getattr(message, "prompt", None)
    return getattr(prompt, "template", str(message))


def _extract_message_role(message):
    role = getattr(message, "role", None)
    if role:
        return str(role).lower()

    message_type_name = type(message).__name__.lower()
    if "system" in message_type_name:
        return "system"
    if "human" in message_type_name or "user" in message_type_name:
        return "user"
    return message_type_name


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
