#embedder.py embeds chunks into vector
import re
from pathlib import Path

import ollama
from ollama import ResponseError
from sentence_transformers import SentenceTransformer


class Embedder:
    BGE_CODE_MODEL_NAMES = {"BAAI/bge-code-v1", "baai/bge-code-v1"}
    BGE_CODE_QUERY_INSTRUCTION = (
        "Given a natural language question about a scientific C++ codebase, "
        "retrieve relevant code, symbol, file, module, or call-chain chunks."
    )
    EMBEDDING_PROMPT_FALLBACKS = [
        None,
        {"generated_explanation": 1500, "code": 5000},
        {"generated_explanation": 750, "code": 3000},
        {"generated_explanation": 250, "code": 1500},
        {"generated_explanation": 0, "code": 800},
    ]

    def __init__(
        self,
        backend="ollama",
        ollama_model="nomic-embed-text",
        transformer_model_name="all-MiniLM-L6-v2",
    ):
        self.backend = backend
        self.ollama_model = ollama_model
        self.transformer_model_name = transformer_model_name
        self.transformer_model = None
        if self.backend == "sentence_transformer":
            model_kwargs = {}
            if self._is_bge_code_model():
                model_kwargs["trust_remote_code"] = True
            self.transformer_model = SentenceTransformer(
                self.transformer_model_name,
                **model_kwargs,
            )
        # Regex pattern to detect file names like Ippl.cpp, BareField.h etc...
        self.file_extension_pattern = re.compile(
            r"\b[A-Za-z0-9_\-]+\.(?:cpp|hpp|h|md|rst|txt)\b",
            re.IGNORECASE,
        )
        self.cpp_code_syntax_pattern = re.compile(
            r"""
            `([^`]*?(?:::|->|\.|<[^`<>]+>|\([^`]*\)|;|\{|\}|\#include)[^`]*)`
            |
            \#include\s*[<"][^>"]+[>"]
            |
            \b[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)+
            (?:\s*<[^>\n]+>)?(?:\s*\([^)\n]*\))?
            |
            \b[A-Za-z_][A-Za-z0-9_]*(?:->|\.)[A-Za-z_][A-Za-z0-9_]*\s*\([^)\n]*\)
            |
            \b[A-Za-z_][A-Za-z0-9_]*\s*<[^>\n]+>\s+[A-Za-z_][A-Za-z0-9_]*\b
            |
            \b[A-Za-z_][A-Za-z0-9_]*\s*\([^)\n]*\)\s*;?
            """,
            re.VERBOSE,
        )
    # returns active backend name, e.g. "ollama" or "sentence_transformer"
    @property
    def embedding_backend(self):
        return self.backend
    
    # returns active embedding model name, e.g. "nomic-embed-text" for ollama or "all-MiniLM-L6-v2" for sentence_transformer
    @property
    def embedding_model_name(self):
        if self.backend == "sentence_transformer":
            return self.transformer_model_name
        return self.ollama_model

    def embed_chunks(self, chunks):
        if self.backend == "sentence_transformer":
            prompts = [self._build_chunk_embedding_prompt(chunk) for chunk in chunks]
            return self.transformer_model.encode(
                prompts,
                normalize_embeddings=True,
            ).tolist()
        return self._ollama_embed(chunks)

    def _ollama_embed(self, chunks):
        embeddings = []
        total_chunks = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            symbol_name = chunk.get("symbol_name", chunk.get("function_name", ""))
            response = None
            last_error = None
            for attempt_index, prompt_limits in enumerate(self.EMBEDDING_PROMPT_FALLBACKS, start=1):
                prompt = self._build_chunk_embedding_prompt(chunk, prompt_limits=prompt_limits)
                try:
                    response = ollama.embeddings(
                        model=self.ollama_model,
                        prompt=prompt,
                    )
                    break
                except ResponseError as exc:
                    last_error = exc
                    if not self._is_context_length_error(exc):
                        raise RuntimeError(
                            f"Embedding failed for {symbol_name} in {chunk['file']} "
                            f"(chunk length: {len(chunk['code'])} chars)."
                        ) from exc
                    if attempt_index < len(self.EMBEDDING_PROMPT_FALLBACKS):
                        print(
                            f"Embedding prompt too long for {symbol_name} in {chunk['file']}; "
                            f"retrying with a shorter prompt (attempt {attempt_index + 1}/"
                            f"{len(self.EMBEDDING_PROMPT_FALLBACKS)})."
                        )
            if response is None:
                raise RuntimeError(
                    f"Embedding failed for {symbol_name} in {chunk['file']} even after "
                    f"shortening the prompt (chunk length: {len(chunk['code'])} chars)."
                ) from last_error
            embeddings.append(response["embedding"])
            if index % 100 == 0 or index == total_chunks:
                print(f"Embedded {index}/{total_chunks} chunks...")
        return embeddings

    def query_embed(self, text):
        prompt = self._build_query_embedding_prompt(text)
        if self.backend == "sentence_transformer":
            encode_kwargs = {}
            if self._is_bge_code_model():
                encode_kwargs["prompt"] = self._bge_code_query_prompt()
            return self.transformer_model.encode(
                [prompt],
                normalize_embeddings=True,
                **encode_kwargs,
            )[0].tolist()

        response = ollama.embeddings(
            model=self.ollama_model,
            prompt=prompt,
        )
        return response["embedding"]

    def _build_chunk_embedding_prompt(self, chunk, prompt_limits=None):
        file_name = Path(chunk["file"]).name
        symbol_name = chunk.get("symbol_name", chunk.get("function_name", ""))
        chunk_type = chunk.get("chunk_type", chunk.get("entity_type", ""))
        parent_symbol = chunk.get("parent_symbol", "")
        namespace_path = chunk.get("namespace_path", "")
        qualified_symbol_name = chunk.get("qualified_symbol_name", "")
        section_path = chunk.get("section_path", chunk.get("parameters", ""))
        limits = prompt_limits or {}
        generated_explanation = self._truncate_for_embedding(
            chunk.get("generated_explanation", ""),
            limits.get("generated_explanation"),
        )
        code = self._truncate_for_embedding(
            chunk.get("code", ""),
            limits.get("code"),
        )

        return f"""
File: {file_name}
Symbol: {symbol_name}
Chunk Type: {chunk_type}
Parent Symbol: {parent_symbol}
Namespace: {namespace_path}
Qualified Symbol: {qualified_symbol_name}
Section Path: {section_path}
Generated Explanation:
{generated_explanation}
Code:
{code}
"""

    def _build_query_embedding_prompt(self, text):
        file_names = self._extract_file_names(text)
        file_name = ", ".join(file_names)
        intent = (
            "find relation across FILES which is asked in QUESTION"
            if len(file_names) > 1
            else self._infer_intent(text)
        )
        chunk_types = self._find_chunk_type(text)
        chunk_type = ", ".join(chunk_types) if chunk_types else "any"
        detected_code = self._extract_detected_code(text)

        sections = []
        if file_name:
            sections.append(f"File: {file_name}")
        if chunk_type:
            sections.append(f"Chunk Type: {chunk_type}")
        if intent:
            sections.append(f"Intent: {intent}")
        sections.append(f"Question:\n{text}")               
        if detected_code:
            sections.append(f"Code:\n{detected_code}")

        return "\n" + "\n".join(sections) + "\n"

    def _is_bge_code_model(self):
        return self.transformer_model_name in self.BGE_CODE_MODEL_NAMES

    def _bge_code_query_prompt(self):
        return f"<instruct>{self.BGE_CODE_QUERY_INSTRUCTION}\n<query>"

    def _extract_file_name(self, text):
        file_names = self._extract_file_names(text)
        return file_names[0] if file_names else ""

    def _extract_file_names(self, text):
        seen = set()
        file_names = []
        for match in self.file_extension_pattern.finditer(text):
            file_name = match.group(0)
            normalized = file_name.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            file_names.append(file_name)
        return file_names

    def _extract_detected_code(self, text):
        seen = set()
        snippets = []
        for match in self.cpp_code_syntax_pattern.finditer(text):
            snippet = match.group(1) or match.group(0)
            snippet = " ".join(snippet.split())
            if not snippet:
                continue
            normalized = snippet.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            snippets.append(snippet)
        return ", ".join(snippets)

    def _infer_intent(self, text):
        lowered = text.lower()
        if "what does" in lowered or "explain" in lowered:
            return "explain retrieved code or documentation"
        if "where" in lowered or "find" in lowered:
            return "locate relevant code or documentation"
        if "how" in lowered:
            return "explain implementation details"
        return "answer question using retrieved context"
    
    def _find_chunk_type(self, text):
        lowered = text.lower()
        chunk_types = []
        if "method" in lowered or "method definition" in lowered:
            chunk_types.append("method_definition, method_declaration")
        if " class " in lowered:
            chunk_types.append("class_or_struct")
        if "data flow" in lowered or "workflow" in lowered:
            chunk_types.append("call_chain_level")
        if " struct " in lowered:
            chunk_types.append("struct")
        if "function" in lowered or "function definition" in lowered:
            chunk_types.append("function_definition")
        if "file" in lowered:
            chunk_types.append("file_level")
        if "module" in lowered:
            chunk_types.append("module_level")
        if " documentation " in lowered:
            chunk_types.append("section, paragraph, code_block")
        return chunk_types 

    def _truncate_for_embedding(self, text, max_chars):
        if max_chars is None:
            return text
        if max_chars <= 0:
            return ""
        if len(text) <= max_chars:
            return text

        marker = "\n[... truncated for embedding ...]\n"
        if max_chars <= len(marker):
            return text[:max_chars]

        head_chars = (max_chars - len(marker)) // 2
        tail_chars = max_chars - len(marker) - head_chars
        return text[:head_chars] + marker + text[-tail_chars:]

    def _is_context_length_error(self, error):
        return "context length" in str(error).lower()
