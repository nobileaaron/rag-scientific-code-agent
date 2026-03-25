
from src.retrieval.reranker import MetadataReranker
from src.retrieval.query_intent_router import QueryIntentRouter
from src.retrieval.structural_expander import StructuralExpander


class Retriever:

    def __init__(
        self,
        embedder,
        vector_store,
        reranker=None,
        candidate_k=20,
        supplementary_k=3,
        supplementary_candidate_k=10,
        structural_expander=None,
        query_intent_router=None,
    ):
        self.embedder = embedder
        self.vector_store = vector_store
        self.reranker = reranker or MetadataReranker()
        self.candidate_k = candidate_k
        self.supplementary_k = supplementary_k
        self.supplementary_candidate_k = supplementary_candidate_k
        self.structural_expander = structural_expander or StructuralExpander(
            vector_store.metadata
        )
        self.query_intent_router = query_intent_router or QueryIntentRouter()

    def retrieve(self, query, k=5):
        result = self.retrieve_with_diagnostics(query, k)
        return result["chunks"]

    def retrieve_with_diagnostics(self, query, k=5):
        exact_filenames = self.reranker.extract_exact_filenames(query)
        exact_symbols = self.reranker.extract_exact_symbols(query)
        intent_result = self.query_intent_router.route(
            query,
            exact_filenames=exact_filenames,
            exact_symbols=exact_symbols,
        )

        # 1 embed the query
        query_embedding = self.embedder.query_embed(query)

        # 2 search the vector store for a wider candidate set
        candidate_count = max(k, self.candidate_k)
        semantic_candidates = self.vector_store.search(query_embedding, candidate_count)
        exact_filename_candidates = self.vector_store.get_chunks_by_filenames(exact_filenames)
        exact_symbol_candidates = self.vector_store.get_chunks_by_symbols(exact_symbols)
        candidates = self._merge_candidates(
            semantic_candidates,
            exact_filename_candidates,
            exact_symbol_candidates,
        )

        # 3 rerank candidates using metadata-aware boosting
        reranked = self.reranker.rerank(
            query,
            candidates,
            k,
            return_diagnostics=True,
        )
        primary_chunks = self._ensure_exact_filename_chunks(
            reranked["chunks"],
            exact_filenames,
            exact_symbols,
            k,
        )
        structural_result = self.structural_expander.expand(
            query,
            primary_chunks,
            mode=intent_result["structural_mode"],
        )
        supplementary_result = self._retrieve_supplementary_chunks(
            query,
            primary_chunks,
        )
        reranked["chunks"] = (
            self._tag_chunks(primary_chunks, "primary")
            + self._tag_chunks(structural_result["chunks"], "structural_expansion")
            + self._tag_chunks(
                supplementary_result["chunks"],
                "supplementary",
            )
        )
        reranked["diagnostics"]["candidate_count"] = len(candidates)
        reranked["diagnostics"]["semantic_candidate_count"] = len(semantic_candidates)
        reranked["diagnostics"]["exact_filename_candidate_count"] = len(exact_filename_candidates)
        reranked["diagnostics"]["exact_symbol_candidate_count"] = len(exact_symbol_candidates)
        reranked["diagnostics"]["query_intent"] = intent_result["intent"]
        reranked["diagnostics"]["query_intent_reasons"] = intent_result["reasons"]
        reranked["diagnostics"]["structural_expansion_mode"] = structural_result["diagnostics"]["mode"]
        reranked["diagnostics"]["structural_expansion_count"] = structural_result["diagnostics"]["count"]
        reranked["diagnostics"]["structural_expansion_reasons"] = structural_result["diagnostics"]["reasons"]
        reranked["diagnostics"]["supplementary_files"] = supplementary_result["files"]
        reranked["diagnostics"]["supplementary_chunk_count"] = len(supplementary_result["chunks"])
        return reranked

    def _merge_candidates(self, semantic_candidates, *injected_candidate_groups):
        merged_candidates = []
        seen_keys = set()

        combined_candidates = []
        for group in injected_candidate_groups:
            combined_candidates.extend(group)
        combined_candidates.extend(semantic_candidates)

        for candidate in combined_candidates:
            chunk = candidate["chunk"]
            chunk_key = (
                chunk.get("file", ""),
                chunk.get("symbol_name", chunk.get("function_name", "")),
                chunk.get("chunk_index", 1),
                chunk.get("code", ""),
            )
            if chunk_key in seen_keys:
                continue
            seen_keys.add(chunk_key)
            merged_candidates.append(candidate)

        return merged_candidates

    def _ensure_exact_filename_chunks(self, chunks, exact_filenames, exact_symbols, k):
        if not exact_filenames and not exact_symbols:
            return chunks[:k]

        exact_filename_chunks = self.vector_store.get_chunks_by_filenames(exact_filenames)
        exact_symbol_chunks = self.vector_store.get_chunks_by_symbols(exact_symbols)
        prioritized_chunks = []
        seen_keys = set()

        for candidate in exact_filename_chunks + exact_symbol_chunks:
            chunk = candidate["chunk"]
            chunk_key = self._chunk_key(chunk)
            if chunk_key in seen_keys:
                continue
            seen_keys.add(chunk_key)
            prioritized_chunks.append(chunk)
            if len(prioritized_chunks) >= k:
                return prioritized_chunks

        for chunk in chunks:
            chunk_key = self._chunk_key(chunk)
            if chunk_key in seen_keys:
                continue
            seen_keys.add(chunk_key)
            prioritized_chunks.append(chunk)
            if len(prioritized_chunks) >= k:
                break

        return prioritized_chunks

    def _chunk_key(self, chunk):
        return (
            chunk.get("file", ""),
            chunk.get("symbol_name", chunk.get("function_name", "")),
            chunk.get("chunk_index", 1),
            chunk.get("code", ""),
        )

    def _retrieve_supplementary_chunks(self, query, primary_chunks):
        referenced_files = self._collect_referenced_files(primary_chunks)
        primary_file_names = {
            str(chunk.get("file_name", "")).lower()
            for chunk in primary_chunks
            if chunk.get("file_name")
        }
        supplementary_files = [
            file_name
            for file_name in referenced_files
            if file_name.lower() not in primary_file_names
        ]

        if not supplementary_files:
            return {"files": [], "chunks": []}

        expanded_query = self._build_supplementary_query(query, primary_chunks, supplementary_files)
        query_embedding = self.embedder.query_embed(expanded_query)
        candidates = self.vector_store.search_in_filenames(
            query_embedding,
            supplementary_files,
            max(self.supplementary_k, self.supplementary_candidate_k),
        )

        reranked = self.reranker.rerank(
            expanded_query,
            candidates,
            self.supplementary_k,
            return_diagnostics=False,
        )

        return {
            "files": supplementary_files,
            "chunks": reranked,
        }

    def _collect_referenced_files(self, chunks):
        referenced_files = []
        seen_files = set()

        for chunk in chunks:
            for file_name in chunk.get("referenced_files", []):
                normalized_name = str(file_name).strip()
                if not normalized_name or normalized_name in seen_files:
                    continue
                seen_files.add(normalized_name)
                referenced_files.append(normalized_name)

        return referenced_files

    def _build_supplementary_query(self, query, primary_chunks, supplementary_files):
        primary_file_names = ", ".join(
            dict.fromkeys(
                str(chunk.get("file_name", ""))
                for chunk in primary_chunks
                if chunk.get("file_name")
            )
        )
        primary_symbols = ", ".join(
            dict.fromkeys(
                str(chunk.get("symbol_name", chunk.get("function_name", "")))
                for chunk in primary_chunks
                if chunk.get("symbol_name", chunk.get("function_name", ""))
            )
        )
        supplementary_file_text = ", ".join(supplementary_files)

        return (
            f"{query}\n"
            f"Primary Files: {primary_file_names}\n"
            f"Primary Symbols: {primary_symbols}\n"
            f"Supplementary Files: {supplementary_file_text}\n"
            "Intent: retrieve supporting chunks from files referenced by the primary results."
        )

    def _tag_chunks(self, chunks, retrieval_role):
        return [{**chunk, "retrieval_role": retrieval_role} for chunk in chunks]
