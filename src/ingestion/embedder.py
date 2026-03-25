#embedder.py embeds chunks into vector
import re
from pathlib import Path

import ollama
from ollama import ResponseError
from sentence_transformers import SentenceTransformer


class Embedder:
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
        for chunk in chunks:
            prompt = self._build_chunk_embedding_prompt(chunk)
            symbol_name = chunk.get("symbol_name", chunk.get("function_name", ""))
            try:
                response = ollama.embeddings(
                    model=self.ollama_model,
                    prompt=prompt,
                )
            except ResponseError as exc:
                raise RuntimeError(
                    f"Embedding failed for {symbol_name} in {chunk['file']} "
                    f"(chunk length: {len(chunk['code'])} chars). Reduce chunk size."
                ) from exc
            embeddings.append(response["embedding"])
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

    def _build_chunk_embedding_prompt(self, chunk):
        file_name = Path(chunk["file"]).name
        symbol_name = chunk.get("symbol_name", chunk.get("function_name", ""))
        source_type = chunk.get("source_type", "")
        chunk_type = chunk.get("chunk_type", chunk.get("entity_type", ""))
        parent_symbol = chunk.get("parent_symbol", "")
        language = chunk.get("language", "")
        section_path = chunk.get("section_path", chunk.get("parameters", ""))
        leading_comment = chunk.get("leading_comment", "")
        generated_explanation = chunk.get("generated_explanation", "")

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
{chunk['code']}
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
