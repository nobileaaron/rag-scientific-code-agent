#embedder.py embeds chunks into vector
import re
from pathlib import Path

import ollama
from ollama import ResponseError
from sentence_transformers import SentenceTransformer


class Embedder:
    EMBEDDING_PROMPT_FALLBACKS = [
        None,
        {"leading_comment": 500, "generated_explanation": 1500, "code": 5000},
        {"leading_comment": 300, "generated_explanation": 750, "code": 3000},
        {"leading_comment": 200, "generated_explanation": 250, "code": 1500},
        {"leading_comment": 0, "generated_explanation": 0, "code": 800},
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
            self.transformer_model = SentenceTransformer(self.transformer_model_name)
        self.file_extension_pattern = re.compile(
            r"\b[A-Za-z0-9_\-]+\.(?:cpp|hpp|h|md|rst|txt)\b",
            re.IGNORECASE,
        )

    @property
    def embedding_backend(self):
        return self.backend

    @property
    def embedding_model_name(self):
        if self.backend == "sentence_transformer":
            return self.transformer_model_name
        return self.ollama_model

    def embed_chunks(self, chunks):
        if self.backend == "sentence_transformer":
            prompts = [self._build_chunk_embedding_prompt(chunk) for chunk in chunks]
            return self.transformer_model.encode(prompts).tolist()
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
            return self.transformer_model.encode([prompt])[0].tolist()

        response = ollama.embeddings(
            model=self.ollama_model,
            prompt=prompt,
        )
        return response["embedding"]

    def _build_chunk_embedding_prompt(self, chunk, prompt_limits=None):
        file_name = Path(chunk["file"]).name
        symbol_name = chunk.get("symbol_name", chunk.get("function_name", ""))
        source_type = chunk.get("source_type", "")
        chunk_type = chunk.get("chunk_type", chunk.get("entity_type", ""))
        parent_symbol = chunk.get("parent_symbol", "")
        language = chunk.get("language", "")
        section_path = chunk.get("section_path", chunk.get("parameters", ""))
        limits = prompt_limits or {}
        leading_comment = self._truncate_for_embedding(
            chunk.get("leading_comment", ""),
            limits.get("leading_comment"),
        )
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
Source Type: {source_type}
Chunk Type: {chunk_type}
Parent Symbol: {parent_symbol}
Language: {language}
Section Path: {section_path}
Leading Comment:
{leading_comment}
Generated Explanation:
{generated_explanation}
Code:
{code}
"""

    def _build_query_embedding_prompt(self, text):
        file_name = self._extract_file_name(text)
        source_type = self._infer_source_type(file_name)
        intent = self._infer_intent(text)

        return f"""
File: {file_name}
Symbol:
Source Type: {source_type}
Chunk Type: query
Parent Symbol:
Language:
Section Path:
Leading Comment:
Intent: {intent}
Code:
{text}
"""

    def _extract_file_name(self, text):
        match = self.file_extension_pattern.search(text)
        return match.group(0) if match else ""

    def _infer_source_type(self, file_name):
        if not file_name:
            return ""

        suffix = Path(file_name).suffix.lower()
        if suffix in {".h", ".hpp"}:
            return "header"
        if suffix == ".cpp":
            return "cpp"
        if suffix in {".md", ".rst", ".txt"}:
            return "documentation"
        return ""

    def _infer_intent(self, text):
        lowered = text.lower()
        if "what does" in lowered or "explain" in lowered:
            return "explain retrieved code or documentation"
        if "where" in lowered or "find" in lowered:
            return "locate relevant code or documentation"
        if "how" in lowered:
            return "explain implementation details"
        return "answer question using retrieved context"

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
