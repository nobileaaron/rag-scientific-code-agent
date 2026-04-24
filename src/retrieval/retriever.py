
from pathlib import Path

from src.retrieval.reranker import MetadataReranker
from src.retrieval.query_intent_router import QueryIntentRouter
from src.retrieval.structural_expander import StructuralExpander


class Retriever:
    # Primary retrieval should prefer a smaller strong set over always filling
    # all k slots with weak tail matches. The gate below keeps a candidate only
    # while its score stays in the same rough quality band as the best results.
    PRIMARY_SCORE_RELATIVE_FLOOR = 0.4
    PRIMARY_SCORE_GAP_THRESHOLD = 8.0
    PRIMARY_SCORE_ABSOLUTE_FLOOR = 1.25
    PRIMARY_SAME_SYMBOL_CAP = 1
    PRIMARY_SAME_FILE_CAP = 2
    DOMINANT_FILE_RATIO = 0.75
    WORKFLOW_KEY_SYMBOLS = frozenset(
        {
            "solve",
            "initializefields",
            "greensfunction",
            "setgradfd",
        }
    )
    WORKFLOW_SYMBOL_PRIORITY = {
        "solve": 0,
        "greensfunction": 1,
        "initializefields": 2,
        "setgradfd": 3,
    }
    DATA_FLOW_ROLE_PRIORITY = {
        "producer": 0,
        "consumer": 1,
        "interpolation": 2,
    }
    DATA_FLOW_CONSUMER_SYMBOLS = frozenset({"gather"})
    DATA_FLOW_INTERPOLATION_SYMBOLS = frozenset({"gatherfromfield", "scattertofield"})
    COMPARISON_ROLE_PRIORITY = {
        "fft_overview": 0,
        "fft_impl": 1,
        "cg_overview": 2,
        "baseline": 3,
    }

    # Scopes/files treated as build or test infrastructure. These are dropped
    # from the final retrieved context unless the query itself is about tests
    # or the build system, because otherwise they displace real code chunks.
    TEST_MODULE_SCOPES = frozenset({"test", "tests", "unit_test", "unit_tests"})
    BUILD_FILE_NAMES = frozenset({"cmakelists.txt"})
    TEST_QUERY_KEYWORDS = (
        "test",
        "tests",
        "unit test",
        "unit_test",
        "unittest",
        "cmake",
        "cmakelists",
        "build",
        "integration test",
    )

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
        api_bearing_terms = self.reranker.extract_api_bearing_terms(query)
        data_flow_direction = self.reranker.extract_data_flow_direction(query)
        data_flow_terms = self.reranker.extract_data_flow_terms(
            query,
            data_flow_direction,
        )
        comparison_subjects = self.reranker.extract_comparison_subjects(query)
        intent_result = self.query_intent_router.route(
            query,
            exact_filenames=exact_filenames,
            exact_symbols=exact_symbols,
        )
        retrieval_preferences = intent_result.get("retrieval_preferences", {})

        # 1 embed the query
        query_embedding = self.embedder.query_embed(query)

        # 2 search the vector store for a wider candidate set
        candidate_count = max(k, self.candidate_k)
        semantic_candidates = self.vector_store.search(query_embedding, candidate_count)
        exact_filename_candidates = self.vector_store.get_chunks_by_filenames(exact_filenames)
        if intent_result.get("intent") == "comparison":
            exact_symbol_candidates = []
            subject_file_candidates = []
            workflow_subject_candidates = []
        else:
            exact_symbol_candidates = self.vector_store.get_chunks_by_symbols(exact_symbols)
            subject_file_candidates = self._retrieve_subject_file_candidates(exact_symbols)
            workflow_subject_candidates = self._retrieve_workflow_subject_candidates(
                exact_symbols,
                query,
                intent_result,
            )
        data_flow_candidates = self._retrieve_data_flow_candidates(
            query,
            intent_result,
            data_flow_terms,
            data_flow_direction,
        )
        comparison_candidates = self._retrieve_comparison_candidates(
            query,
            intent_result,
            comparison_subjects,
        )
        literal_api_candidates = self._retrieve_literal_api_candidates(
            api_bearing_terms,
            query,
            intent_result,
        )
        target_aligned_candidates = self._retrieve_target_aligned_candidates(
            exact_symbols,
            retrieval_preferences,
        )
        candidates = self._merge_candidates(
            semantic_candidates,
            exact_filename_candidates,
            exact_symbol_candidates,
            subject_file_candidates,
            workflow_subject_candidates,
            data_flow_candidates,
            comparison_candidates,
            literal_api_candidates,
            target_aligned_candidates,
        )

        # 3 rerank candidates using metadata-aware boosting
        reranked = self.reranker.rerank(
            query,
            candidates,
            k,
            return_diagnostics=True,
            retrieval_preferences=retrieval_preferences,
        )
        primary_candidate_selection = self._select_primary_candidates(
            reranked["diagnostics"].get("reranked_candidates", []),
            k,
        )
        primary_selected_candidates = self._refine_primary_candidates(
            primary_candidate_selection["selected"],
            reranked["diagnostics"].get("reranked_candidates", []),
            k,
            exact_symbols,
            api_bearing_terms,
            data_flow_terms,
            data_flow_direction,
            comparison_subjects,
            intent_result,
        )
        primary_chunks = self._ensure_exact_filename_chunks(
            [candidate["chunk"] for candidate in primary_selected_candidates],
            exact_filenames,
            exact_symbols,
            k,
            retrieval_preferences=retrieval_preferences,
            intent_result=intent_result,
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
        combined_chunks = (
            self._tag_chunks(primary_chunks, "primary")
            + self._tag_chunks(structural_result["chunks"], "structural_expansion")
            + self._tag_chunks(
                supplementary_result["chunks"],
                "supplementary",
            )
        )
        filtered_chunks, filter_diagnostics = self._filter_noise_chunks(
            combined_chunks,
            query,
            intent_result,
        )
        reranked["chunks"] = filtered_chunks
        reranked["diagnostics"]["candidate_count"] = len(candidates)
        reranked["diagnostics"]["semantic_candidate_count"] = len(semantic_candidates)
        reranked["diagnostics"]["exact_filename_candidate_count"] = len(exact_filename_candidates)
        reranked["diagnostics"]["exact_symbol_candidate_count"] = len(exact_symbol_candidates)
        reranked["diagnostics"]["subject_file_candidate_count"] = len(subject_file_candidates)
        reranked["diagnostics"]["workflow_subject_candidate_count"] = len(
            workflow_subject_candidates
        )
        reranked["diagnostics"]["data_flow_direction"] = data_flow_direction
        reranked["diagnostics"]["data_flow_terms"] = sorted(data_flow_terms)
        reranked["diagnostics"]["data_flow_candidate_count"] = len(data_flow_candidates)
        reranked["diagnostics"]["comparison_subjects"] = comparison_subjects
        reranked["diagnostics"]["comparison_candidate_count"] = len(comparison_candidates)
        reranked["diagnostics"]["api_bearing_terms"] = sorted(api_bearing_terms)
        reranked["diagnostics"]["literal_api_candidate_count"] = len(literal_api_candidates)
        reranked["diagnostics"]["target_aligned_candidate_count"] = len(
            target_aligned_candidates
        )
        reranked["diagnostics"]["primary_selected_count"] = len(
            primary_selected_candidates
        )
        reranked["diagnostics"]["primary_score_filtered_count"] = len(
            primary_candidate_selection["filtered_out"]
        )
        reranked["diagnostics"]["primary_score_gate"] = primary_candidate_selection[
            "gate"
        ]
        reranked["diagnostics"]["primary_score_filtered_candidates"] = (
            primary_candidate_selection["filtered_out"]
        )
        reranked["diagnostics"]["primary_selection_strategy"] = (
            "location_api_coverage_plus_diversity"
            if (
                intent_result.get("intent") == "location_lookup"
                and api_bearing_terms
            )
            else (
                "data_flow_role_coverage_plus_diversity"
                if intent_result.get("intent") == "data_flow"
                else (
                    "comparison_side_coverage_plus_diversity"
                    if intent_result.get("intent") == "comparison"
                    else "score_gate_plus_diversity"
                )
            )
        )
        reranked["diagnostics"]["query_intent"] = intent_result["intent"]
        reranked["diagnostics"]["query_intent_reasons"] = intent_result["reasons"]
        reranked["diagnostics"]["entity_target"] = intent_result.get("entity_target", "")
        reranked["diagnostics"]["preferred_entity_levels"] = list(
            retrieval_preferences.get("preferred_entity_levels", ())
        )
        reranked["diagnostics"]["preferred_chunk_types"] = list(
            retrieval_preferences.get("preferred_chunk_types", ())
        )
        reranked["diagnostics"]["structural_expansion_mode"] = structural_result["diagnostics"]["mode"]
        reranked["diagnostics"]["structural_expansion_count"] = structural_result["diagnostics"]["count"]
        reranked["diagnostics"]["structural_expansion_reasons"] = structural_result["diagnostics"]["reasons"]
        reranked["diagnostics"]["supplementary_files"] = supplementary_result["files"]
        reranked["diagnostics"]["supplementary_chunk_count"] = len(supplementary_result["chunks"])
        reranked["diagnostics"]["noise_filter"] = filter_diagnostics
        return reranked

    def _refine_primary_candidates(
        self,
        selected_candidates,
        reranked_candidates,
        k,
        exact_symbols,
        api_bearing_terms,
        data_flow_terms,
        data_flow_direction,
        comparison_subjects,
        intent_result,
    ):
        refined_candidates = self._refine_location_primary_candidates(
            selected_candidates,
            reranked_candidates,
            k,
            api_bearing_terms,
            intent_result,
        )
        refined_candidates = self._refine_data_flow_primary_candidates(
            refined_candidates,
            reranked_candidates,
            k,
            data_flow_terms,
            data_flow_direction,
            intent_result,
        )
        refined_candidates = self._refine_comparison_primary_candidates(
            refined_candidates,
            reranked_candidates,
            k,
            comparison_subjects,
            intent_result,
        )
        if intent_result.get("intent") == "comparison":
            return refined_candidates[:k]
        return self._diversify_primary_candidates(
            refined_candidates,
            reranked_candidates,
            k,
            exact_symbols,
            intent_result,
        )

    def _refine_location_primary_candidates(
        self,
        selected_candidates,
        reranked_candidates,
        k,
        api_bearing_terms,
        intent_result,
    ):
        """Keep location-query primaries tightly centered on exact API evidence.

        Without this refinement, the normal score gate can still keep nearby
        helper/status functions such as `Environment::initialized` because they
        lexically match words like "initialized" and "finalized". For a query
        like "Where is Kokkos initialized and finalized?", that creates prompt
        dilution even though the reranker already found the real `Ippl.cpp`
        call sites.

        Strategy:
        - only activate for `location_lookup` queries with inferred API terms
        - walk candidates in reranked order
        - keep only candidates that literally match at least one requested API term
        - stop as soon as the selected set covers all requested API terms

        This keeps the final prompt focused on source-of-truth call sites
        instead of padding with semantically nearby lifecycle helpers.
        """

        if intent_result.get("intent") != "location_lookup":
            return selected_candidates
        if not api_bearing_terms:
            return selected_candidates

        candidate_pool = []
        seen_candidates = set()
        for candidate in list(selected_candidates) + list(reranked_candidates):
            candidate_key = self._chunk_key(candidate["chunk"])
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)
            candidate_pool.append(candidate)

        candidate_pool = self._sort_primary_candidate_pool(
            candidate_pool,
            exact_symbols,
            intent_result,
        )

        prioritized_candidates = []
        covered_terms = set()
        seen_chunks = set()

        for candidate in candidate_pool:
            matched_api_terms = candidate.get("matched_api_terms", [])
            if not matched_api_terms:
                continue

            chunk_key = self._chunk_key(candidate["chunk"])
            if chunk_key in seen_chunks:
                continue

            seen_chunks.add(chunk_key)
            prioritized_candidates.append(candidate)
            covered_terms.update(matched_api_terms)

            if covered_terms >= set(api_bearing_terms):
                break
            if len(prioritized_candidates) >= k:
                break

        if prioritized_candidates:
            return prioritized_candidates[:k]

        return selected_candidates

    def _refine_data_flow_primary_candidates(
        self,
        selected_candidates,
        reranked_candidates,
        k,
        data_flow_terms,
        data_flow_direction,
        intent_result,
    ):
        """Ensure data-flow queries cover producer, consumer, and interpolation.

        A handoff query like "How does the electric field flow from the grid
        back to particles after a poisson solve?" needs evidence from multiple
        modules:

        - a producer chunk showing the field exists on the grid
        - a consumer chunk showing particle code gathers that field
        - an interpolation chunk showing how the transfer is computed

        Semantic search tends to stay in the producer file. This refinement
        keeps the final primary set coverage-oriented by selecting one strong
        chunk per role when available.
        """

        if intent_result.get("intent") != "data_flow":
            return selected_candidates
        if not data_flow_direction:
            return selected_candidates

        candidate_pool = []
        seen_candidates = set()
        for candidate in list(selected_candidates) + list(reranked_candidates):
            candidate_key = self._chunk_key(candidate["chunk"])
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)
            candidate_pool.append(candidate)

        candidate_pool = self._sort_data_flow_candidate_pool(candidate_pool)

        selected_by_role = {}
        fallback_candidates = []
        seen_chunks = set()

        for candidate in candidate_pool:
            chunk = candidate["chunk"]
            chunk_key = self._chunk_key(chunk)
            if chunk_key in seen_chunks:
                continue
            seen_chunks.add(chunk_key)

            role = self._classify_data_flow_role(chunk)
            if role and role not in selected_by_role:
                selected_by_role[role] = candidate
            else:
                fallback_candidates.append(candidate)

        prioritized = [
            selected_by_role[role]
            for role in ("producer", "consumer", "interpolation")
            if role in selected_by_role
        ]

        for candidate in fallback_candidates:
            if len(prioritized) >= k:
                break
            prioritized.append(candidate)

        if prioritized:
            return prioritized[:k]

        return selected_candidates

    def _refine_comparison_primary_candidates(
        self,
        selected_candidates,
        reranked_candidates,
        k,
        comparison_subjects,
        intent_result,
    ):
        """Ensure comparison queries cover both named sides plus a baseline.

        Example:
        - FFT-side Poisson solver
        - CG-side Poisson solver
        - shared Poisson interface / baseline

        Without this step, broad exact-symbol matches such as `FFT` can fill
        every primary slot with one side of the comparison.
        """

        if intent_result.get("intent") != "comparison":
            return selected_candidates
        if not comparison_subjects:
            return selected_candidates

        candidate_pool = []
        seen_candidates = set()
        for candidate in list(selected_candidates) + list(reranked_candidates):
            candidate_key = self._chunk_key(candidate["chunk"])
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)
            candidate_pool.append(candidate)

        candidate_pool = self._sort_comparison_candidate_pool(candidate_pool, comparison_subjects)

        selected_by_role = {}
        fallback_candidates = []
        seen_chunks = set()

        for candidate in candidate_pool:
            chunk = candidate["chunk"]
            chunk_key = self._chunk_key(chunk)
            if chunk_key in seen_chunks:
                continue
            seen_chunks.add(chunk_key)

            role = self._classify_comparison_role(chunk, comparison_subjects)
            if role and role not in selected_by_role:
                selected_by_role[role] = candidate
            else:
                fallback_candidates.append(candidate)

        prioritized = [
            selected_by_role[role]
            for role in ("fft_overview", "fft_impl", "cg_overview", "baseline")
            if role in selected_by_role
        ]

        desired_roles = {"fft_overview", "fft_impl", "cg_overview", "baseline"}
        if desired_roles.issubset(set(selected_by_role)):
            return prioritized[:k]

        for candidate in fallback_candidates:
            if len(prioritized) >= k:
                break
            prioritized.append(candidate)

        if prioritized:
            return prioritized[:k]

        return selected_candidates

    def _diversify_primary_candidates(
        self,
        selected_candidates,
        reranked_candidates,
        k,
        exact_symbols,
        intent_result,
    ):
        """Reduce same-symbol/file flooding in the final primary set.

        Two related failures are handled here:

        1. Exact-symbol injection can overfill the primary set with many
           adjacent chunks from the same symbol, e.g. fourteen `Poisson` class
           chunks from `Poisson.h`.
        2. When almost every strong candidate points at the same file, the LLM
           usually benefits more from that file's file-level entity plus one or
           two key method chunks than from a wall of neighboring symbol chunks.
        """

        candidate_pool = []
        seen_candidates = set()
        for candidate in list(selected_candidates) + list(reranked_candidates):
            candidate_key = self._chunk_key(candidate["chunk"])
            if candidate_key in seen_candidates:
                continue
            seen_candidates.add(candidate_key)
            candidate_pool.append(candidate)

        dominant_file_path = self._detect_dominant_file(selected_candidates)
        dominant_file_level_candidate = None
        if dominant_file_path:
            for candidate in candidate_pool:
                chunk = candidate["chunk"]
                file_path = chunk.get("path", chunk.get("file", ""))
                if (
                    file_path == dominant_file_path
                    and str(chunk.get("entity_level", "") or "") == "file_level"
                ):
                    dominant_file_level_candidate = candidate
                    break

        diversified = []
        seen_chunks = set()
        symbol_counts = {}
        file_counts = {}
        dominant_non_file_count = 0
        dominant_non_file_cap = 2 if intent_result.get("intent") == "workflow_explanation" else 1

        if dominant_file_level_candidate is not None:
            chunk = dominant_file_level_candidate["chunk"]
            chunk_key = self._chunk_key(chunk)
            diversified.append(dominant_file_level_candidate)
            seen_chunks.add(chunk_key)
            file_path = chunk.get("path", chunk.get("file", ""))
            file_counts[file_path] = 1

        for candidate in candidate_pool:
            chunk = candidate["chunk"]
            chunk_key = self._chunk_key(chunk)
            if chunk_key in seen_chunks:
                continue

            file_path = chunk.get("path", chunk.get("file", ""))
            symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "").lower()
            symbol_group = (file_path, symbol_name)
            entity_level = str(chunk.get("entity_level", "") or "")
            chunk_type = str(chunk.get("chunk_type", chunk.get("entity_type", "")) or "")
            injection_reason = str(candidate.get("injection_reason", "") or "")
            exact_subject_file = self._file_matches_exact_symbol(chunk, exact_symbols)
            file_name = str(chunk.get("file_name", "") or "").lower()
            file_stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
            path_lower = file_path.lower()

            # For workflow questions, once we have anchored the relevant solver
            # file, plain class-definition chunks from that same subject file
            # add much less value than `solve()` / `greensFunction()` or the
            # file-level summary. Skip those broad class chunks so they do not
            # crowd out the implementation path.
            if (
                intent_result.get("intent") == "workflow_explanation"
                and exact_subject_file
                and chunk_type == "class"
                and not injection_reason
            ):
                continue

            if (
                intent_result.get("intent") == "workflow_explanation"
                and exact_subject_file
                and symbol_name in exact_symbols
                and symbol_name == file_stem
                and not injection_reason
            ):
                continue

            if intent_result.get("intent") == "data_flow":
                if not any(
                    marker in path_lower
                    for marker in ("/poissonsolvers/", "/particle/", "/interpolation/")
                ):
                    continue

            if symbol_counts.get(symbol_group, 0) >= self.PRIMARY_SAME_SYMBOL_CAP:
                continue

            if dominant_file_path and file_path == dominant_file_path:
                if entity_level == "file_level":
                    continue
                if dominant_non_file_count >= dominant_non_file_cap:
                    continue

            if file_counts.get(file_path, 0) >= self.PRIMARY_SAME_FILE_CAP and entity_level != "file_level":
                continue

            diversified.append(candidate)
            seen_chunks.add(chunk_key)
            symbol_counts[symbol_group] = symbol_counts.get(symbol_group, 0) + 1
            file_counts[file_path] = file_counts.get(file_path, 0) + 1

            if dominant_file_path and file_path == dominant_file_path and entity_level != "file_level":
                dominant_non_file_count += 1

            if len(diversified) >= k:
                break

        if diversified:
            return diversified[:k]

        return selected_candidates

    def _sort_primary_candidate_pool(self, candidate_pool, exact_symbols, intent_result):
        if intent_result.get("intent") != "workflow_explanation":
            return candidate_pool

        exact_symbols = {str(symbol).lower() for symbol in (exact_symbols or set()) if symbol}

        def sort_key(candidate):
            chunk = candidate["chunk"]
            injection_reason = str(candidate.get("injection_reason", "") or "")
            entity_level = str(chunk.get("entity_level", "") or "")
            symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "").lower()
            exact_subject_file = self._file_matches_exact_symbol(chunk, exact_symbols)

            priority = 99
            if injection_reason == "subject_file_alignment":
                priority = 0
            elif injection_reason == "workflow_subject_alignment":
                priority = 1 + self.WORKFLOW_SYMBOL_PRIORITY.get(symbol_name, 10)
            elif entity_level == "file_level" and exact_subject_file:
                priority = 10
            elif symbol_name in self.WORKFLOW_KEY_SYMBOLS and exact_subject_file:
                priority = 20 + self.WORKFLOW_SYMBOL_PRIORITY.get(symbol_name, 10)
            elif exact_subject_file:
                priority = 40

            return (
                priority,
                -float(candidate.get("combined_score", 0.0)),
                str(chunk.get("path", chunk.get("file", ""))),
                symbol_name,
            )

        return sorted(candidate_pool, key=sort_key)

    def _sort_data_flow_candidate_pool(self, candidate_pool):
        def sort_key(candidate):
            chunk = candidate["chunk"]
            role = self._classify_data_flow_role(chunk)
            symbol_name = str(
                chunk.get("symbol_name", chunk.get("function_name", "")) or ""
            ).lower()
            entity_level = str(chunk.get("entity_level", "") or "")
            path = str(chunk.get("path", chunk.get("file", "")) or "").lower()

            role_detail_priority = 5
            if role == "consumer" and symbol_name == "gather":
                role_detail_priority = 0
            elif role == "interpolation" and symbol_name in self.DATA_FLOW_INTERPOLATION_SYMBOLS:
                role_detail_priority = 0
            elif role == "interpolation" and entity_level in {"function_level", "call_chain_level"}:
                role_detail_priority = 1
            elif role == "producer" and symbol_name == "solve":
                role_detail_priority = 0
                if "/fft" in path:
                    role_detail_priority = -1
            return (
                self.DATA_FLOW_ROLE_PRIORITY.get(role, 99),
                role_detail_priority,
                -float(candidate.get("combined_score", 0.0)),
                path,
                symbol_name,
            )

        return sorted(candidate_pool, key=sort_key)

    def _sort_comparison_candidate_pool(self, candidate_pool, comparison_subjects):
        def sort_key(candidate):
            chunk = candidate["chunk"]
            role = self._classify_comparison_role(chunk, comparison_subjects)
            return (
                self.COMPARISON_ROLE_PRIORITY.get(role, 99),
                -float(candidate.get("combined_score", 0.0)),
                str(chunk.get("path", chunk.get("file", ""))),
                str(chunk.get("symbol_name", chunk.get("function_name", ""))).lower(),
            )

        return sorted(candidate_pool, key=sort_key)

    def _retrieve_literal_api_candidates(self, api_bearing_terms, query, intent_result):
        """Inject exact call-site candidates for lifecycle/location queries.

        Semantic retrieval is good at finding conceptually related files such
        as environment/setup code, but it can still miss the one source file
        that literally contains `Library::initialize` or `Library::finalize`.
        This helper scans stored chunk text for those concrete API terms and
        adds matching chunks back into the candidate pool before reranking.

        The injection is intentionally narrow:
        - only for location-style queries
        - only when we inferred explicit API-bearing terms
        - tests/build files stay excluded unless the query asks about them
        """

        if intent_result.get("intent") != "location_lookup":
            return []
        if not api_bearing_terms:
            return []

        query_mentions_tests = self._query_mentions_tests(query)
        injected_candidates = []
        seen_keys = set()

        for chunk in self.vector_store.metadata:
            if not query_mentions_tests:
                if self._is_test_scope_chunk(chunk) or self._is_build_file_chunk(chunk):
                    continue

            matched_api_terms = self.reranker.match_api_bearing_terms(
                chunk,
                api_bearing_terms,
            )
            if not matched_api_terms:
                continue

            chunk_key = self._chunk_key(chunk)
            if chunk_key in seen_keys:
                continue
            seen_keys.add(chunk_key)

            # Use a moderate synthetic distance instead of 0.0. We want these
            # candidates in the pool even when semantic search missed them, but
            # we still want the reranker to decide among several exact matches
            # using path/source/entity evidence instead of a perfect semantic
            # score dominating everything.
            coverage = len(matched_api_terms) / max(len(api_bearing_terms), 1)
            distance = max(0.2, 0.85 - (0.35 * coverage))
            if str(chunk.get("source_type", "")).lower() == "cpp":
                distance = max(0.15, distance - 0.05)

            injected_candidates.append(
                {
                    "chunk": chunk,
                    "distance": distance,
                    "injected": True,
                    "injection_reason": "literal_api_match",
                    "matched_api_terms": matched_api_terms,
                }
            )

        injected_candidates.sort(
            key=lambda candidate: (
                candidate["distance"],
                -len(candidate.get("matched_api_terms", [])),
                str(
                    candidate["chunk"].get(
                        "path",
                        candidate["chunk"].get("file", ""),
                    )
                ),
            )
        )
        return injected_candidates[: max(self.candidate_k, 10)]

    def _retrieve_subject_file_candidates(self, exact_symbols):
        """Inject file-level chunks whose file stem matches a named subject.

        This bridges natural-language subject mentions such as
        `FFTOpenPoissonSolver` to the corresponding file-level entity even when
        the query does not explicitly ask for a file. It is especially useful
        for workflow questions, where the file-level chunk gives the retriever a
        stable anchor before structural expansion fans out to solver methods.
        """

        exact_symbols = {str(symbol).lower() for symbol in (exact_symbols or set()) if symbol}
        if not exact_symbols:
            return []

        injected_candidates = []
        seen_keys = set()

        for chunk in self.vector_store.metadata:
            if str(chunk.get("entity_level", "") or "") != "file_level":
                continue
            if not self._file_matches_exact_symbol(chunk, exact_symbols):
                continue

            chunk_key = self._chunk_key(chunk)
            if chunk_key in seen_keys:
                continue
            seen_keys.add(chunk_key)

            distance = 0.2
            if str(chunk.get("source_type", "")).lower() == "header":
                distance = 0.25

            injected_candidates.append(
                {
                    "chunk": chunk,
                    "distance": distance,
                    "injected": True,
                    "injection_reason": "subject_file_alignment",
                }
            )

        return injected_candidates

    def _retrieve_workflow_subject_candidates(self, exact_symbols, query, intent_result):
        """Inject key implementation methods from a subject-matched solver file."""

        if intent_result.get("intent") != "workflow_explanation":
            return []

        exact_symbols = {str(symbol).lower() for symbol in (exact_symbols or set()) if symbol}
        if not exact_symbols:
            return []

        query_mentions_tests = self._query_mentions_tests(query)
        matched_file_paths = set()
        for chunk in self.vector_store.metadata:
            if self._file_matches_exact_symbol(chunk, exact_symbols):
                matched_file_paths.add(chunk.get("path", chunk.get("file", "")))

        if not matched_file_paths:
            return []

        injected_candidates = []
        seen_symbol_groups = set()

        for chunk in self.vector_store.metadata:
            file_path = chunk.get("path", chunk.get("file", ""))
            if file_path not in matched_file_paths:
                continue

            if not query_mentions_tests:
                if self._is_test_scope_chunk(chunk) or self._is_build_file_chunk(chunk):
                    continue

            symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "").lower()
            if symbol_name not in self.WORKFLOW_KEY_SYMBOLS:
                continue

            chunk_type = str(chunk.get("chunk_type", chunk.get("entity_type", "")) or "")
            if chunk_type not in {"function_definition", "method_definition", "call_chain_level"}:
                continue

            symbol_group = (file_path, symbol_name)
            if symbol_group in seen_symbol_groups:
                continue
            seen_symbol_groups.add(symbol_group)

            distance = 0.18 if chunk_type in {"function_definition", "method_definition"} else 0.24
            injected_candidates.append(
                {
                    "chunk": chunk,
                    "distance": distance,
                    "injected": True,
                    "injection_reason": "workflow_subject_alignment",
                }
            )

        injected_candidates.sort(
            key=lambda candidate: (
                self.WORKFLOW_SYMBOL_PRIORITY.get(
                    str(
                        candidate["chunk"].get(
                            "symbol_name",
                            candidate["chunk"].get("function_name", ""),
                        )
                    ).lower(),
                    99,
                ),
                candidate["distance"],
                str(candidate["chunk"].get("path", candidate["chunk"].get("file", ""))),
            )
        )
        return injected_candidates

    def _retrieve_data_flow_candidates(
        self,
        query,
        intent_result,
        data_flow_terms,
        data_flow_direction,
    ):
        """Inject chunks that explain a cross-module data handoff.

        For grid/field <-> particle questions we want at least three kinds of
        evidence in the candidate pool:

        - a producer (`solve` in a Poisson solver)
        - a consumer (`ParticleAttrib::gather` / `scatter`)
        - an interpolation helper (`gatherFromField` / `scatterToField`)

        This helper injects those cross-module anchors directly instead of
        hoping semantic retrieval will jump from one subsystem to another.
        """

        if intent_result.get("intent") != "data_flow":
            return []
        if not data_flow_direction or not data_flow_terms:
            return []

        query_mentions_tests = self._query_mentions_tests(query)
        best_by_role = {}

        for chunk in self.vector_store.metadata:
            if not query_mentions_tests:
                if self._is_test_scope_chunk(chunk) or self._is_build_file_chunk(chunk):
                    continue

            role = self._classify_data_flow_role(chunk)
            if not role:
                continue

            matched_terms = self.reranker.match_data_flow_terms(chunk, data_flow_terms)
            if not matched_terms and role != "producer":
                continue

            if role == "producer" and "poisson" in query.lower():
                path = str(chunk.get("path", chunk.get("file", "")) or "").lower()
                if "/poissonsolvers/" not in path:
                    continue
                symbol_name = str(
                    chunk.get("symbol_name", chunk.get("function_name", "")) or ""
                ).lower()
                if symbol_name != "solve":
                    continue

            distance = {
                "producer": 0.23,
                "consumer": 0.14,
                "interpolation": 0.12,
            }.get(role, 0.25)
            candidate = {
                "chunk": chunk,
                "distance": distance,
                "injected": True,
                "injection_reason": f"data_flow_{role}",
            }
            sort_key = self._data_flow_injection_sort_key(candidate, role)
            best_entry = best_by_role.get(role)
            if best_entry is None or sort_key < best_entry["sort_key"]:
                best_by_role[role] = {
                    "candidate": candidate,
                    "sort_key": sort_key,
                }

        injected_candidates = [
            best_by_role[role]["candidate"]
            for role in ("producer", "consumer", "interpolation")
            if role in best_by_role
        ]
        injected_candidates.sort(
            key=lambda candidate: (
                self.DATA_FLOW_ROLE_PRIORITY.get(
                    self._classify_data_flow_role(candidate["chunk"]),
                    99,
                ),
                candidate["distance"],
                str(candidate["chunk"].get("path", candidate["chunk"].get("file", ""))),
            )
        )
        return injected_candidates

    def _retrieve_comparison_candidates(
        self,
        query,
        intent_result,
        comparison_subjects,
    ):
        """Inject comparison-side anchors for solver tradeoff queries."""

        if intent_result.get("intent") != "comparison":
            return []
        if not comparison_subjects:
            return []

        query_mentions_tests = self._query_mentions_tests(query)
        best_by_role = {}

        for chunk in self.vector_store.metadata:
            if not query_mentions_tests:
                if self._is_test_scope_chunk(chunk) or self._is_build_file_chunk(chunk):
                    continue

            role = self._classify_comparison_role(chunk, comparison_subjects)
            if not role:
                continue

            candidate = {
                "chunk": chunk,
                "distance": {
                    "fft_overview": 0.12,
                    "fft_impl": 0.10,
                    "cg_overview": 0.11,
                    "baseline": 0.16,
                }.get(role, 0.2),
                "injected": True,
                "injection_reason": f"comparison_{role}",
            }
            sort_key = self._comparison_injection_sort_key(candidate, role)
            best_entry = best_by_role.get(role)
            if best_entry is None or sort_key < best_entry["sort_key"]:
                best_by_role[role] = {
                    "candidate": candidate,
                    "sort_key": sort_key,
                }

        injected_candidates = [
            best_by_role[role]["candidate"]
            for role in ("fft_overview", "fft_impl", "cg_overview", "baseline")
            if role in best_by_role
        ]
        injected_candidates.sort(
            key=lambda candidate: (
                self.COMPARISON_ROLE_PRIORITY.get(
                    self._classify_comparison_role(candidate["chunk"], comparison_subjects),
                    99,
                ),
                candidate["distance"],
                str(candidate["chunk"].get("path", candidate["chunk"].get("file", ""))),
            )
        )
        return injected_candidates

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

    def _ensure_exact_filename_chunks(
        self,
        chunks,
        exact_filenames,
        exact_symbols,
        k,
        retrieval_preferences=None,
        intent_result=None,
    ):
        # At this point "chunks" already passed reranking and the low-score
        # gate, so exact matches should only be reordered within this accepted
        # subset. We intentionally do not re-fetch exact chunks from the vector
        # store here, because that could smuggle weak tail matches back into the
        # primary context after the score gate excluded them.
        if not exact_filenames and not exact_symbols:
            return chunks[:k]

        if (intent_result or {}).get("intent") == "comparison":
            return chunks[:k]

        # If the refined selection already contains file-level chunks whose file
        # stems match the subject symbols, preserve that order. This avoids
        # undoing the diversity pass for descriptive workflow queries such as
        # "FFT-Based Open-Boundary Poisson Solver", where synthesized exact
        # symbols should anchor the right file, but not push a wall of class
        # chunks ahead of the promoted file-level entity.
        if not exact_filenames:
            normalized_exact_symbols = {
                str(symbol).lower() for symbol in (exact_symbols or set()) if symbol
            }
            has_subject_file_level_chunk = any(
                str(chunk.get("entity_level", "") or "") == "file_level"
                and self._file_matches_exact_symbol(chunk, normalized_exact_symbols)
                for chunk in chunks
            )
            if has_subject_file_level_chunk:
                return chunks[:k]

        prioritized_chunks = []
        seen_keys = set()

        # First keep exact matches that already survived reranking and score
        # filtering, preserving the reranker's entity-aware ordering. This
        # avoids a metadata-order fallback where exact symbol collisions (for
        # example many chunks named "FFT") can undo the explicit module/file/
        # function preference from the query itself.
        for chunk in chunks:
            if not self._chunk_matches_exact_target(chunk, exact_filenames, exact_symbols):
                continue
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

    def _chunk_matches_exact_target(self, chunk, exact_filenames, exact_symbols):
        file_name = str(chunk.get("file_name", "")).lower()
        symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", ""))).lower()
        return file_name in exact_filenames or symbol_name in exact_symbols

    def _file_matches_exact_symbol(self, chunk, exact_symbols):
        file_path = str(chunk.get("path", chunk.get("file", "")) or "")
        file_name = str(chunk.get("file_name", "") or "").lower()
        base_name = str(chunk.get("base_name", "") or "").lower()
        file_stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
        path_stem = Path(file_path).stem.lower() if file_path else ""
        return (
            file_stem in exact_symbols
            or base_name in exact_symbols
            or path_stem in exact_symbols
        )

    def _detect_dominant_file(self, selected_candidates):
        if not selected_candidates:
            return ""

        file_counts = {}
        for candidate in selected_candidates:
            file_path = candidate["chunk"].get("path", candidate["chunk"].get("file", ""))
            if not file_path:
                continue
            file_counts[file_path] = file_counts.get(file_path, 0) + 1

        if not file_counts:
            return ""

        dominant_file_path, dominant_count = max(file_counts.items(), key=lambda item: item[1])
        total_count = len(selected_candidates)
        if dominant_count == total_count:
            return dominant_file_path
        if dominant_count >= 3 and (dominant_count / total_count) >= self.DOMINANT_FILE_RATIO:
            return dominant_file_path
        return ""

    def _classify_data_flow_role(self, chunk):
        path = str(chunk.get("path", chunk.get("file", "")) or "").lower()
        symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "").lower()
        searchable_text = self.reranker._build_chunk_search_text(chunk)
        normalized_text = searchable_text.replace(" ", "")

        if "/poissonsolvers/" in path and symbol_name == "solve":
            return "producer"

        if (
            "/particle/" in path
            and symbol_name in self.DATA_FLOW_CONSUMER_SYMBOLS
        ):
            return "consumer"

        if (
            "/interpolation/" in path
            or symbol_name in self.DATA_FLOW_INTERPOLATION_SYMBOLS
            or "gatherfromfield" in normalized_text
            or "scattertofield" in normalized_text
        ):
            return "interpolation"

        return ""

    def _classify_comparison_role(self, chunk, comparison_subjects):
        comparison_role = self.reranker.classify_comparison_subject(chunk, comparison_subjects)
        path = str(chunk.get("path", chunk.get("file", "")) or "").lower()
        entity_level = str(chunk.get("entity_level", "") or "")
        chunk_type = str(chunk.get("chunk_type", chunk.get("entity_type", "")) or "")
        symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "").lower()

        if comparison_role == "fft":
            if (
                "fftperiodicpoissonsolver" in path
                and symbol_name == "solve"
                and chunk_type in {"method_definition", "function_definition"}
            ):
                return "fft_impl"
            if entity_level == "file_level" or chunk_type == "class":
                return "fft_overview"

        if comparison_role == "cg":
            if entity_level == "file_level" or chunk_type == "class":
                return "cg_overview"

        if comparison_role == "baseline":
            if entity_level == "file_level" or chunk_type == "class":
                return "baseline"

        return ""

    def _data_flow_injection_sort_key(self, candidate, role):
        chunk = candidate["chunk"]
        path = str(chunk.get("path", chunk.get("file", "")) or "").lower()
        symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "").lower()
        entity_level = str(chunk.get("entity_level", "") or "")
        normalized_text = self.reranker._build_chunk_search_text(chunk).replace(" ", "")

        if role == "producer":
            chunk_type = str(chunk.get("chunk_type", chunk.get("entity_type", "")) or "")
            return (
                0 if "/fft" in path else 1,
                0 if chunk_type in {"function_definition", "method_definition"} else 1,
                0 if symbol_name == "solve" else 1,
                path,
            )

        if role == "consumer":
            return (
                0 if symbol_name == "gather" else 1,
                0 if entity_level == "function_level" else 1,
                path,
            )

        if role == "interpolation":
            return (
                0 if "gatherfromfield" in normalized_text else 1,
                0 if symbol_name in self.DATA_FLOW_INTERPOLATION_SYMBOLS else 1,
                0 if entity_level in {"function_level", "call_chain_level"} else 1,
                path,
            )

        return (path,)

    def _comparison_injection_sort_key(self, candidate, role):
        chunk = candidate["chunk"]
        path = str(chunk.get("path", chunk.get("file", "")) or "").lower()
        symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "").lower()
        chunk_type = str(chunk.get("chunk_type", chunk.get("entity_type", "")) or "")
        entity_level = str(chunk.get("entity_level", "") or "")

        if role == "fft_impl":
            return (
                0 if path.endswith("fftperiodicpoissonsolver.hpp") else 1,
                0 if symbol_name == "solve" else 1,
                0 if chunk_type in {"method_definition", "function_definition"} else 1,
                path,
            )

        if role == "fft_overview":
            return (
                0 if path.endswith("fftperiodicpoissonsolver.h") else 1,
                0 if entity_level == "file_level" else 1,
                path,
            )

        if role == "cg_overview":
            return (
                0 if path.endswith("poissoncg.h") else 1,
                0 if entity_level == "file_level" else 1,
                path,
            )

        if role == "baseline":
            return (
                0 if path.endswith("poisson.h") else 1,
                0 if entity_level == "file_level" else 1,
                path,
            )

        return (path,)

    def _prioritize_exact_chunks_for_target(self, chunks, retrieval_preferences):
        preferred_entity_levels = {
            str(entity_level)
            for entity_level in (retrieval_preferences or {}).get(
                "preferred_entity_levels",
                (),
            )
            if entity_level
        }
        preferred_chunk_types = {
            str(chunk_type)
            for chunk_type in (retrieval_preferences or {}).get(
                "preferred_chunk_types",
                (),
            )
            if chunk_type
        }

        def sort_key(chunk):
            entity_level = str(chunk.get("entity_level", "") or "")
            chunk_type = str(chunk.get("chunk_type", chunk.get("entity_type", "")) or "")
            symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "")
            file_path = str(chunk.get("path", chunk.get("file", "")) or "")
            return (
                0 if entity_level in preferred_entity_levels else 1,
                0 if chunk_type in preferred_chunk_types else 1,
                file_path,
                symbol_name,
            )

        return sorted(chunks, key=sort_key)

    def _select_primary_candidates(self, reranked_candidates, k):
        """Keep only the strong prefix of reranked candidates for primary use.

        The retrieval system can still keep broader candidates in diagnostics,
        but the final primary set should not be padded with obviously weak tail
        results just to hit k. The gate is intentionally conservative:

        - always keep the top candidate
        - keep following candidates while they stay in the same rough score band
        - once a candidate drops far below the best result and also shows a
          strong cliff from the previous accepted score, stop accepting the tail

        This works better than a single absolute threshold because retrieval
        scores vary a lot across query types.
        """

        if not reranked_candidates:
            return {
                "selected": [],
                "filtered_out": [],
                "gate": {},
            }

        top_score = float(reranked_candidates[0].get("combined_score", 0.0))
        relative_floor_score = top_score * self.PRIMARY_SCORE_RELATIVE_FLOOR
        minimum_allowed_score = max(
            self.PRIMARY_SCORE_ABSOLUTE_FLOOR,
            relative_floor_score,
        )

        selected = [reranked_candidates[0]]
        filtered_out = []
        stop_reason = "kept_top_k_or_fewer"
        stop_index = None

        for index, candidate in enumerate(reranked_candidates[1:], start=2):
            if len(selected) >= k:
                break

            current_score = float(candidate.get("combined_score", 0.0))
            previous_score = float(selected[-1].get("combined_score", 0.0))
            below_relative_floor = current_score < relative_floor_score
            below_absolute_floor = current_score < self.PRIMARY_SCORE_ABSOLUTE_FLOOR
            large_gap_from_previous = (
                previous_score - current_score
            ) >= self.PRIMARY_SCORE_GAP_THRESHOLD

            if below_relative_floor and (below_absolute_floor or large_gap_from_previous):
                filtered_out.append(candidate)
                filtered_out.extend(reranked_candidates[index:])
                stop_reason = "stopped_on_large_score_cliff"
                stop_index = index
                break

            selected.append(candidate)

        return {
            "selected": selected,
            "filtered_out": filtered_out,
            "gate": {
                "top_score": top_score,
                "relative_floor": self.PRIMARY_SCORE_RELATIVE_FLOOR,
                "relative_floor_score": relative_floor_score,
                "absolute_floor": self.PRIMARY_SCORE_ABSOLUTE_FLOOR,
                "minimum_allowed_score": minimum_allowed_score,
                "gap_threshold": self.PRIMARY_SCORE_GAP_THRESHOLD,
                "stop_reason": stop_reason,
                "stop_index": stop_index,
            },
        }

    def _retrieve_target_aligned_candidates(self, exact_symbols, retrieval_preferences):
        """Inject higher-level candidates that match the query's named subject.

        Exact symbol lookup works well when the requested entity and the stored
        symbol share the same name. File-level chunks are a common exception:
        users often ask for "the FFT file", while the stored file-level symbols
        are named ``FFT.h`` or ``FFT.hpp`` rather than ``FFT``. This helper
        bridges that gap by injecting entity-target-specific candidates from
        metadata before reranking.
        """

        exact_symbols = {
            str(symbol).lower()
            for symbol in (exact_symbols or set())
            if symbol
        }
        if not exact_symbols:
            return []

        entity_target = str(
            (retrieval_preferences or {}).get("entity_target", "") or ""
        )
        if not entity_target:
            return []

        injected_candidates = []
        seen_keys = set()

        for chunk in self.vector_store.metadata:
            if not self._chunk_matches_target_aligned_exact_symbol(
                chunk,
                exact_symbols,
                entity_target,
            ):
                continue

            chunk_key = self._chunk_key(chunk)
            if chunk_key in seen_keys:
                continue
            seen_keys.add(chunk_key)
            injected_candidates.append(
                {
                    "chunk": chunk,
                    "distance": 0.0,
                    "injected": True,
                    "injection_reason": "entity_target_alignment",
                }
            )

        return injected_candidates

    def _chunk_matches_target_aligned_exact_symbol(
        self,
        chunk,
        exact_symbols,
        entity_target,
    ):
        entity_level = str(chunk.get("entity_level", "") or "")
        symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "").lower()
        module_key = str(chunk.get("module_key", "") or "").lower()
        module_path = str(chunk.get("module_path", "") or "").lower()
        base_name = str(chunk.get("base_name", "") or "").lower()
        file_name = str(chunk.get("file_name", "") or "").lower()
        file_stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name

        if entity_target == "file_level" and entity_level == "file_level":
            return (
                symbol_name in exact_symbols
                or base_name in exact_symbols
                or file_stem in exact_symbols
            )

        if entity_target == "module_level" and entity_level == "module_level":
            module_key_tail = module_key.split(":")[-1] if ":" in module_key else module_key
            module_path_tail = module_path.split("/")[-1] if "/" in module_path else module_path
            return (
                symbol_name in exact_symbols
                or module_key_tail in exact_symbols
                or module_path_tail in exact_symbols
            )

        if entity_target == "call_chain_level" and entity_level == "call_chain_level":
            return symbol_name in exact_symbols

        if entity_target == "function_level" and entity_level == "function_level":
            return symbol_name in exact_symbols

        if (
            entity_target == "documentation_section_level"
            and entity_level == "documentation_section_level"
        ):
            return symbol_name in exact_symbols or base_name in exact_symbols

        return False

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
            retrieval_preferences=None,
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

    def _filter_noise_chunks(self, chunks, query, intent_result):
        """Drop chunks that are structurally adjacent but unhelpful for the query.

        Two classes of noise are handled here:

        1. Build/test infrastructure (``test:*`` / ``unit_tests:*`` module
           scopes, ``CMakeLists.txt`` files). These get pulled in by module
           expansion because the test tree mirrors source module names, but
           they displace real content when the user is asking about code
           behavior rather than the build system. Dropped unless the query
           explicitly mentions tests or cmake.

        2. Call-chain supplementary chunks for ``module_overview`` queries.
           Supplementary retrieval is seeded by files referenced from primary
           chunks, which for module questions pulls in unrelated accessor
           methods (e.g. ``BareField::getIndex``) just because FFT code calls
           them. Those entries dilute the context without answering the
           question.

        Diagnostics record every drop so debug mode still shows what was cut.
        """

        query_mentions_tests = self._query_mentions_tests(query)
        intent = intent_result.get("intent", "")
        kept = []
        dropped = []

        for chunk in chunks:
            drop_reasons = []

            if not query_mentions_tests:
                if self._is_test_scope_chunk(chunk):
                    drop_reasons.append("test_scope_without_test_query")
                if self._is_build_file_chunk(chunk):
                    drop_reasons.append("build_file_without_test_query")

            if (
                intent == "module_overview"
                and chunk.get("retrieval_role") == "supplementary"
                and chunk.get("entity_level") == "call_chain_level"
            ):
                drop_reasons.append("call_chain_supplementary_for_module_overview")

            if drop_reasons:
                dropped.append(
                    {
                        "path": chunk.get("path", chunk.get("file", "")),
                        "symbol_name": chunk.get(
                            "symbol_name", chunk.get("function_name", "")
                        ),
                        "entity_level": chunk.get("entity_level", ""),
                        "retrieval_role": chunk.get("retrieval_role", ""),
                        "reasons": drop_reasons,
                    }
                )
                continue

            kept.append(chunk)

        diagnostics = {
            "query_mentions_tests": query_mentions_tests,
            "intent": intent,
            "dropped_count": len(dropped),
            "dropped": dropped,
        }
        return kept, diagnostics

    def _query_mentions_tests(self, query):
        lowered = query.lower()
        return any(keyword in lowered for keyword in self.TEST_QUERY_KEYWORDS)

    def _is_test_scope_chunk(self, chunk):
        module_scope = str(chunk.get("module_scope", "") or "").lower()
        return module_scope in self.TEST_MODULE_SCOPES

    def _is_build_file_chunk(self, chunk):
        file_name = str(chunk.get("file_name", "") or "").lower()
        return file_name in self.BUILD_FILE_NAMES
