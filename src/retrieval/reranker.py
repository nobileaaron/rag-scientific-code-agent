import re
from pathlib import Path


class MetadataReranker:
    def __init__(self):
        self.file_extension_pattern = re.compile(
            r"\b[A-Za-z0-9_\-]+\.(?:cpp|hpp|h|md|rst|txt)\b",
            re.IGNORECASE,
        )
        self.token_pattern = re.compile(r"[A-Za-z0-9_./-]+")
        self.low_signal_tokens = {"h", "hpp", "cpp", "md", "rst", "txt"}
        self.query_stopwords = {
            "a",
            "an",
            "and",
            "about",
            "class",
            "code",
            "component",
            "describe",
            "do",
            "does",
            "explain",
            "file",
            "for",
            "function",
            "header",
            "how",
            "in",
            "is",
            "me",
            "module",
            "of",
            "tell",
            "the",
            "this",
            "what",
            "where",
            "which",
        }

    def rerank(self, query, candidates, k=5, return_diagnostics=False):
        normalized_query = query.lower()
        query_tokens = self._extract_query_tokens(query)
        exact_filenames = self.extract_exact_filenames(query)
        exact_symbols = self.extract_exact_symbols(query)

        rescored_candidates = []
        for candidate in candidates:
            chunk = candidate["chunk"]
            distance = candidate["distance"]
            semantic_score = 1.0 / (1.0 + max(distance, 0.0))
            metadata_score = self._metadata_score(
                normalized_query,
                query_tokens,
                exact_filenames,
                exact_symbols,
                chunk,
            )
            combined_score = semantic_score + metadata_score

            rescored_candidates.append(
                {
                    "chunk": chunk,
                    "distance": distance,
                    "semantic_score": semantic_score,
                    "metadata_score": metadata_score,
                    "combined_score": combined_score,
                }
            )

        rescored_candidates.sort(
            key=lambda candidate: candidate["combined_score"],
            reverse=True,
        )

        top_candidates = rescored_candidates[:k]

        if return_diagnostics:
            return {
                "chunks": [candidate["chunk"] for candidate in top_candidates],
                "diagnostics": {
                    "query_tokens": sorted(query_tokens),
                    "exact_filenames": sorted(exact_filenames),
                    "exact_symbols": sorted(exact_symbols),
                    "reranked_candidates": rescored_candidates,
                },
            }

        return [candidate["chunk"] for candidate in top_candidates]

    def _metadata_score(self, normalized_query, query_tokens, exact_filenames, exact_symbols, chunk):
        score = 0.0
        file_name = str(chunk.get("file_name", Path(chunk.get("file", "")).name)).lower()
        path = str(chunk.get("path", chunk.get("file", ""))).lower()
        symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", ""))).lower()
        source_type = str(chunk.get("source_type", "")).lower()

        if exact_filenames and file_name in exact_filenames:
            score += 20.0
        if exact_symbols and symbol_name in exact_symbols:
            score += 20.0

        file_name_tokens = self._split_metadata_tokens(file_name)
        path_tokens = self._split_metadata_tokens(path)
        symbol_tokens = self._split_metadata_tokens(symbol_name)

        meaningful_query_tokens = query_tokens - self.low_signal_tokens
        meaningful_file_name_tokens = file_name_tokens - self.low_signal_tokens
        meaningful_path_tokens = path_tokens - self.low_signal_tokens
        meaningful_symbol_tokens = symbol_tokens - self.low_signal_tokens

        file_name_overlap = len(meaningful_query_tokens & meaningful_file_name_tokens)
        path_overlap = len(meaningful_query_tokens & meaningful_path_tokens)
        symbol_overlap = len(meaningful_query_tokens & meaningful_symbol_tokens)

        if exact_filenames and file_name in exact_filenames and file_name_overlap > 0:
            score += 4.0
        if exact_symbols and symbol_name in exact_symbols and symbol_overlap > 0:
            score += 4.0

        score += 4.0 * file_name_overlap
        score += 2.0 * path_overlap
        score += 2.0 * symbol_overlap

        if any(filename.endswith((".hpp", ".h")) for filename in exact_filenames) and source_type == "header":
            score += 1.0
        if any(filename.endswith(".cpp") for filename in exact_filenames) and source_type == "cpp":
            score += 1.0
        if any(filename.endswith((".md", ".rst", ".txt")) for filename in exact_filenames) and source_type == "documentation":
            score += 1.0

        if "header" in query_tokens and source_type == "header":
            score += 0.5
        if any(token in {"cpp", "implementation", "source"} for token in query_tokens) and source_type == "cpp":
            score += 0.5
        if any(token in {"doc", "docs", "documentation", "readme"} for token in query_tokens) and source_type == "documentation":
            score += 0.5

        if file_name and file_name in normalized_query:
            score += 8.0
        if symbol_name and symbol_name in normalized_query:
            score += 8.0
        if exact_symbols and symbol_name in exact_symbols and source_type in {"cpp", "header"}:
            score += 2.0

        return score

    def extract_exact_filenames(self, query):
        return {
            match.group(0).lower()
            for match in self.file_extension_pattern.finditer(query)
        }

    def extract_exact_symbols(self, query):
        symbols = set()
        for raw_token in self.token_pattern.findall(query):
            token = raw_token.lower()
            if token in self.query_stopwords:
                continue
            if token in self.low_signal_tokens:
                continue
            if "." in token or "/" in token:
                continue
            if len(token) < 3:
                continue
            symbols.add(token)
        return symbols

    def _extract_query_tokens(self, query):
        tokens = set()
        for raw_token in self.token_pattern.findall(query.lower()):
            tokens.add(raw_token)
            tokens.update(self._split_metadata_tokens(raw_token))
        return {token for token in tokens if token}

    def _split_metadata_tokens(self, text):
        normalized_text = text.lower().replace("\\", "/")
        split_parts = re.split(r"[^a-z0-9]+", normalized_text)
        return {part for part in split_parts if part}
