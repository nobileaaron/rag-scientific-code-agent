
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
        exact_symbol_candidates = self.vector_store.get_chunks_by_symbols(exact_symbols)
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
        primary_selected_candidates = self._refine_location_primary_candidates(
            primary_candidate_selection["selected"],
            reranked["diagnostics"].get("reranked_candidates", []),
            k,
            api_bearing_terms,
            intent_result,
        )
        primary_chunks = self._ensure_exact_filename_chunks(
            [candidate["chunk"] for candidate in primary_selected_candidates],
            exact_filenames,
            exact_symbols,
            k,
            retrieval_preferences=retrieval_preferences,
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
            "location_api_coverage"
            if (
                intent_result.get("intent") == "location_lookup"
                and api_bearing_terms
            )
            else "score_gate"
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
    ):
        # At this point "chunks" already passed reranking and the low-score
        # gate, so exact matches should only be reordered within this accepted
        # subset. We intentionally do not re-fetch exact chunks from the vector
        # store here, because that could smuggle weak tail matches back into the
        # primary context after the score gate excluded them.
        if not exact_filenames and not exact_symbols:
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
