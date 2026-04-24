import re
from pathlib import Path


class MetadataReranker:
    # Exact API-call matches matter disproportionately for location/lifecycle
    # queries such as "Where is Kokkos initialized and finalized?". In those
    # cases the user is usually looking for the concrete source location of a
    # literal call site, not just thematically related infrastructure.
    LOCATION_QUERY_KEYWORDS = (
        "where",
        "find",
        "located",
        "implemented",
        "defined",
        "initialize",
        "initialized",
        "initialise",
        "initialised",
        "finalize",
        "finalized",
        "finalise",
        "finalised",
        "setup",
        "set up",
        "teardown",
        "tear down",
    )

    # These query phrases often refer to a concrete lifecycle call in code.
    # We normalize them to the code spelling we expect to see inside chunks.
    LIFECYCLE_ACTION_ALIASES = {
        "initialize": "initialize",
        "initialized": "initialize",
        "initialise": "initialize",
        "initialised": "initialize",
        "finalize": "finalize",
        "finalized": "finalize",
        "finalise": "finalize",
        "finalised": "finalize",
        "setup": "setup",
        "set up": "setup",
        "teardown": "teardown",
        "tear down": "teardown",
    }

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

    TEST_MODULE_SCOPES = frozenset({"test", "tests", "unit_test", "unit_tests"})

    ENTITY_TARGET_WEIGHTS = {
        # Strong enough to overcome many exact-symbol collisions such as "FFT",
        # where dozens of symbol-level chunks share the same lexical signal but
        # the query explicitly asks for a module/file/call-chain entity first.
        "preferred_entity_level": 14.0,
        # Used when the target entity matches the named subject in a
        # target-specific way, such as a file-level chunk whose base name is
        # "FFT" for the query "explain the FFT file".
        "target_subject_match": 14.0,
        # A smaller extra nudge for subtype hints such as "class" or "method".
        "preferred_chunk_type": 5.0,
        # Mild penalty for tracked entity levels that clearly do not match the
        # user's explicit request. This keeps non-preferred chunks eligible,
        # but makes it less likely that they outrank the requested entity kind.
        "mismatched_entity_level": -8.0,
    }

    TRACKED_ENTITY_LEVELS = {
        "function_level",
        "file_level",
        "module_level",
        "call_chain_level",
        "documentation_section_level",
    }

    def __init__(self):
        self.file_extension_pattern = re.compile(
            r"\b[A-Za-z0-9_\-]+\.(?:cpp|hpp|h|md|rst|txt)\b",
            re.IGNORECASE,
        )
        self.token_pattern = re.compile(r"[A-Za-z0-9_./-]+")
        self.identifier_pattern = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
        self.namespaced_identifier_pattern = re.compile(
            r"\b(?:[A-Za-z_][A-Za-z0-9_]*::)+[A-Za-z_][A-Za-z0-9_]*\b"
        )
        self.subject_before_action_pattern = re.compile(
            r"\b(?P<subject>[A-Za-z_][A-Za-z0-9_:]*)\s+"
            r"(?:is\s+)?"
            r"(?P<action>initialized|initialised|finalized|finalised|setup|teardown)\b",
            re.IGNORECASE,
        )
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

    def rerank(
        self,
        query,
        candidates,
        k=5,
        return_diagnostics=False,
        retrieval_preferences=None,
    ):
        normalized_query = query.lower()
        query_tokens = self._extract_query_tokens(query)
        exact_filenames = self.extract_exact_filenames(query)
        exact_symbols = self.extract_exact_symbols(query)
        api_bearing_terms = self.extract_api_bearing_terms(query)
        retrieval_preferences = retrieval_preferences or {}

        rescored_candidates = []
        for candidate in candidates:
            chunk = candidate["chunk"]
            distance = candidate["distance"]
            semantic_score = 1.0 / (1.0 + max(distance, 0.0))
            metadata_result = self._metadata_score(
                normalized_query,
                query_tokens,
                exact_filenames,
                exact_symbols,
                api_bearing_terms,
                chunk,
            )
            lexical_metadata_score = metadata_result["score"]
            entity_target_score = self._entity_target_score(
                chunk,
                retrieval_preferences,
                exact_symbols,
            )
            metadata_score = lexical_metadata_score + entity_target_score
            combined_score = semantic_score + metadata_score

            rescored_candidates.append(
                {
                    **candidate,
                    "chunk": chunk,
                    "distance": distance,
                    "semantic_score": semantic_score,
                    "lexical_metadata_score": lexical_metadata_score,
                    "api_term_score": metadata_result["api_term_score"],
                    "matched_api_terms": metadata_result["matched_api_terms"],
                    "entity_target_score": entity_target_score,
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
                    "api_bearing_terms": sorted(api_bearing_terms),
                    "entity_target": retrieval_preferences.get("entity_target", ""),
                    "preferred_entity_levels": list(
                        retrieval_preferences.get("preferred_entity_levels", ())
                    ),
                    "preferred_chunk_types": list(
                        retrieval_preferences.get("preferred_chunk_types", ())
                    ),
                    "reranked_candidates": rescored_candidates,
                },
            }

        return [candidate["chunk"] for candidate in top_candidates]

    def _metadata_score(
        self,
        normalized_query,
        query_tokens,
        exact_filenames,
        exact_symbols,
        api_bearing_terms,
        chunk,
    ):
        score = 0.0
        file_name = str(chunk.get("file_name", Path(chunk.get("file", "")).name)).lower()
        path = str(chunk.get("path", chunk.get("file", ""))).lower()
        symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", ""))).lower()
        source_type = str(chunk.get("source_type", "")).lower()
        entity_level = str(chunk.get("entity_level", "")).lower()
        matched_api_terms = []
        api_term_score = 0.0

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

        if self._looks_like_location_query(normalized_query) and api_bearing_terms:
            matched_api_terms = self.match_api_bearing_terms(chunk, api_bearing_terms)
            if matched_api_terms:
                api_term_score += 14.0 * len(matched_api_terms)
                # Reward chunks that cover the whole lifecycle requested by the
                # user, e.g. both `Kokkos::initialize` and `Kokkos::finalize`.
                if len(matched_api_terms) == len(api_bearing_terms) and len(api_bearing_terms) > 1:
                    api_term_score += 10.0
                if source_type == "cpp":
                    api_term_score += 8.0
                if "/src/" in path:
                    api_term_score += 8.0
                if source_type == "documentation":
                    api_term_score -= 10.0
                if entity_level == "function_level":
                    api_term_score += 3.0
                lifecycle_actions = {
                    term.rsplit("::", 1)[-1]
                    for term in api_bearing_terms
                    if "::" in term
                }
                if symbol_name in lifecycle_actions:
                    api_term_score += 6.0

            # Test executables often contain the same API calls as the real
            # source of truth. Penalize them for non-test location queries so
            # literal test matches do not outrank the library/runtime path.
            if (
                matched_api_terms
                and not self._query_mentions_tests(normalized_query)
                and self._is_test_scope_chunk(chunk)
            ):
                api_term_score -= 12.0

        score += api_term_score
        return {
            "score": score,
            "api_term_score": api_term_score,
            "matched_api_terms": matched_api_terms,
        }

    def _entity_target_score(self, chunk, retrieval_preferences, exact_symbols):
        """Score how well a chunk matches an explicit entity-level request.

        This layer intentionally sits on top of the normal lexical metadata
        score. The lexical score answers "does this chunk look related to the
        query tokens?", while this method answers "is this the kind of entity
        the user explicitly asked for?".

        Example:
        - Query: "explain the FFT module"
        - Symbol-level chunks named FFT are still lexically relevant.
        - Module-level chunks should nevertheless win the primary ranking.
        """

        explicit_target = str(retrieval_preferences.get("entity_target", "") or "")
        preferred_entity_levels = {
            str(entity_level)
            for entity_level in retrieval_preferences.get("preferred_entity_levels", ())
            if entity_level
        }
        preferred_chunk_types = {
            str(chunk_type)
            for chunk_type in retrieval_preferences.get("preferred_chunk_types", ())
            if chunk_type
        }

        if not explicit_target and not preferred_entity_levels and not preferred_chunk_types:
            return 0.0

        entity_level = str(chunk.get("entity_level", "") or "")
        chunk_type = str(chunk.get("chunk_type", chunk.get("entity_type", "")) or "")
        score = 0.0

        if preferred_entity_levels and entity_level in preferred_entity_levels:
            score += self.ENTITY_TARGET_WEIGHTS["preferred_entity_level"]
        elif explicit_target and entity_level in self.TRACKED_ENTITY_LEVELS:
            score += self.ENTITY_TARGET_WEIGHTS["mismatched_entity_level"]

        if self._chunk_matches_target_subject(chunk, explicit_target, exact_symbols):
            score += self.ENTITY_TARGET_WEIGHTS["target_subject_match"]

        if preferred_chunk_types and chunk_type in preferred_chunk_types:
            score += self.ENTITY_TARGET_WEIGHTS["preferred_chunk_type"]

        return score

    def _chunk_matches_target_subject(self, chunk, explicit_target, exact_symbols):
        if not explicit_target or not exact_symbols:
            return False

        exact_symbols = {str(symbol).lower() for symbol in exact_symbols if symbol}
        entity_level = str(chunk.get("entity_level", "") or "")
        symbol_name = str(chunk.get("symbol_name", chunk.get("function_name", "")) or "").lower()
        module_key = str(chunk.get("module_key", "") or "").lower()
        module_path = str(chunk.get("module_path", "") or "").lower()
        base_name = str(chunk.get("base_name", "") or "").lower()
        file_name = str(chunk.get("file_name", "") or "").lower()
        file_stem = file_name.rsplit(".", 1)[0] if "." in file_name else file_name

        if explicit_target == "file_level" and entity_level == "file_level":
            return (
                symbol_name in exact_symbols
                or base_name in exact_symbols
                or file_stem in exact_symbols
            )

        if explicit_target == "module_level" and entity_level == "module_level":
            module_key_tail = module_key.split(":")[-1] if ":" in module_key else module_key
            module_path_tail = module_path.split("/")[-1] if "/" in module_path else module_path
            return (
                symbol_name in exact_symbols
                or module_key_tail in exact_symbols
                or module_path_tail in exact_symbols
            )

        if explicit_target == "call_chain_level" and entity_level == "call_chain_level":
            return symbol_name in exact_symbols

        if explicit_target == "function_level" and entity_level == "function_level":
            return symbol_name in exact_symbols

        if (
            explicit_target == "documentation_section_level"
            and entity_level == "documentation_section_level"
        ):
            return symbol_name in exact_symbols or base_name in exact_symbols

        return False

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

    def extract_api_bearing_terms(self, query):
        """Infer literal code terms worth rescuing into the candidate pool.

        Examples:
        - "Where is Kokkos initialized and finalized?" ->
          {"kokkos::initialize", "kokkos::finalize"}
        - "Where is Kokkos::initialize called?" ->
          {"kokkos::initialize"}

        These terms are intentionally narrower than generic query tokens. They
        are used to recover exact call-site chunks that semantic retrieval can
        miss when nearby lifecycle/setup files are semantically similar.
        """

        lowered_query = query.lower()
        api_terms = {
            match.group(0).lower()
            for match in self.namespaced_identifier_pattern.finditer(query)
        }

        lifecycle_actions = self._extract_lifecycle_actions(lowered_query)
        if not lifecycle_actions:
            return api_terms

        subjects = self._extract_lifecycle_subjects(query)
        for subject in subjects:
            normalized_subject = subject.lower()
            for action in lifecycle_actions:
                api_terms.add(f"{normalized_subject}::{action}")

        return api_terms

    def match_api_bearing_terms(self, chunk, api_terms):
        if not api_terms:
            return []

        searchable_text = self._build_chunk_search_text(chunk)
        matched_terms = sorted(
            term for term in api_terms if term and term in searchable_text
        )
        return matched_terms

    def _extract_query_tokens(self, query):
        tokens = set()
        for raw_token in self.token_pattern.findall(query.lower()):
            tokens.add(raw_token)
            tokens.update(self._split_metadata_tokens(raw_token))
        return {token for token in tokens if token}

    def _looks_like_location_query(self, lowered_query):
        return any(keyword in lowered_query for keyword in self.LOCATION_QUERY_KEYWORDS)

    def _extract_lifecycle_actions(self, lowered_query):
        actions = set()
        for phrase, canonical_action in self.LIFECYCLE_ACTION_ALIASES.items():
            if phrase in lowered_query:
                actions.add(canonical_action)
        return actions

    def _extract_lifecycle_subjects(self, query):
        subjects = []
        seen = set()

        for match in self.subject_before_action_pattern.finditer(query):
            subject = match.group("subject")
            normalized_subject = subject.lower()
            if normalized_subject in self.query_stopwords:
                continue
            if normalized_subject in seen:
                continue
            seen.add(normalized_subject)
            subjects.append(subject)

        if subjects:
            return subjects

        # Fallback: if the query mentions lifecycle language but not in a neat
        # "X initialized" form, keep the first code-like capitalized token as
        # the most likely API/library subject. This is intentionally conservative
        # to avoid fabricating many namespace guesses from ordinary prose.
        for token in self.identifier_pattern.findall(query):
            if not token:
                continue
            if not token[0].isupper():
                continue
            normalized_token = token.lower()
            if normalized_token in self.query_stopwords:
                continue
            subjects.append(token)
            break

        return subjects

    def _query_mentions_tests(self, lowered_query):
        return any(keyword in lowered_query for keyword in self.TEST_QUERY_KEYWORDS)

    def _is_test_scope_chunk(self, chunk):
        module_scope = str(chunk.get("module_scope", "") or "").lower()
        return module_scope in self.TEST_MODULE_SCOPES

    def _build_chunk_search_text(self, chunk):
        search_fields = [
            chunk.get("code", ""),
            chunk.get("generated_explanation", ""),
            chunk.get("path", chunk.get("file", "")),
            chunk.get("file_name", ""),
            chunk.get("symbol_name", chunk.get("function_name", "")),
            chunk.get("function_name", ""),
            chunk.get("leading_comment", ""),
        ]
        return "\n".join(str(field) for field in search_fields if field).lower()

    def _split_metadata_tokens(self, text):
        normalized_text = text.lower().replace("\\", "/")
        split_parts = re.split(r"[^a-z0-9]+", normalized_text)
        return {part for part in split_parts if part}
