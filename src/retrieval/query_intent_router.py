class QueryIntentRouter:
    # adjust intent-to-expansion mapping here later if retrieval feels too narrow or too broad.
    INTENT_PROFILES = {
        "location_lookup": {
            "structural_mode": "mode_1_minimal",
        },
        "data_flow": {
            "structural_mode": "mode_3_broad",
        },
        "comparison": {
            "structural_mode": "mode_2_balanced",
        },
        "symbol_explanation": {
            "structural_mode": "mode_2_balanced",
        },
        "file_purpose": {
            "structural_mode": "mode_2_balanced",
        },
        "module_overview": {
            "structural_mode": "mode_2_balanced",
        },
        "workflow_explanation": {
            "structural_mode": "mode_3_broad",
        },
        "default": {
            "structural_mode": "mode_2_balanced",
        },
    }

    # These profiles let the query router express not only "what kind of answer
    # is being asked for?" but also "what kind of stored entity should retrieval
    # prefer as the primary evidence?". That second part is important for
    # queries such as "explain the FFT module" where the lexical symbol "FFT"
    # may match many symbol-level chunks, but the user's wording clearly asks
    # for a module-level entity first.
    ENTITY_TARGET_PROFILES = {
        "file_level": {
            "preferred_entity_levels": ("file_level",),
            "preferred_chunk_types": ("file_level",),
        },
        "module_level": {
            "preferred_entity_levels": ("module_level",),
            "preferred_chunk_types": ("module_level",),
        },
        "call_chain_level": {
            "preferred_entity_levels": ("call_chain_level",),
            "preferred_chunk_types": ("call_chain_level",),
        },
        "function_level": {
            "preferred_entity_levels": ("function_level",),
            "preferred_chunk_types": (),
        },
        "documentation_section_level": {
            "preferred_entity_levels": ("documentation_section_level",),
            "preferred_chunk_types": ("section", "paragraph", "code_block"),
        },
    }

    # These are more specific chunk-type hints layered on top of the broad
    # entity-level preference. For example, "class FFT" still targets the
    # symbol-level entity pool overall, but we can additionally boost chunks
    # whose chunk type is actually "class".
    SYMBOL_LEVEL_CHUNK_HINTS = {
        "class": ("class",),
        "struct": ("struct",),
        "method": ("method_definition", "method_declaration"),
        "function": ("function_definition", "method_definition"),
        "routine": ("function_definition", "method_definition"),
    }

    def route(self, query, exact_filenames=None, exact_symbols=None):
        exact_filenames = exact_filenames or set()
        exact_symbols = exact_symbols or set()
        lowered = query.lower()
        reasons = []
        entity_target = self._detect_entity_target(lowered)
        if entity_target:
            reasons.append(f"matched_{entity_target}_keywords")

        if self._contains_any(
            lowered,
            (
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
            ),
        ):
            reasons.append("matched_location_keywords")
            return self._result("location_lookup", reasons, lowered, entity_target)

        if self._looks_like_data_flow_query(lowered):
            reasons.append("matched_data_flow_keywords")
            return self._result("data_flow", reasons, lowered, entity_target)

        if self._looks_like_comparison_query(lowered):
            reasons.append("matched_comparison_keywords")
            return self._result("comparison", reasons, lowered, entity_target)

        if self._contains_any(
            lowered,
            ("how does", "workflow", "pipeline", "process", "compute", "calculation", "call chain"),
        ):
            reasons.append("matched_workflow_keywords")
            return self._result("workflow_explanation", reasons, lowered, entity_target)

        if self._contains_any(
            lowered,
            ("module", "subsystem", "folder", "package", "directory"),
        ):
            reasons.append("matched_module_keywords")
            return self._result("module_overview", reasons, lowered, entity_target)

        if exact_filenames:
            reasons.append("detected_exact_filename")
            return self._result("file_purpose", reasons, lowered, entity_target)

        if exact_symbols:
            reasons.append("detected_exact_symbol")
            return self._result("symbol_explanation", reasons, lowered, entity_target)

        reasons.append("fell_back_to_default")
        return self._result("default", reasons, lowered, entity_target)

    def _result(self, intent, reasons, lowered_query, entity_target):
        profile = self.INTENT_PROFILES[intent]
        retrieval_preferences = self._build_retrieval_preferences(
            lowered_query,
            entity_target,
        )
        return {
            "intent": intent,
            "structural_mode": profile["structural_mode"],
            "reasons": reasons,
            "entity_target": entity_target,
            "retrieval_preferences": retrieval_preferences,
        }

    def _contains_any(self, lowered_query, phrases):
        return any(phrase in lowered_query for phrase in phrases)

    def _looks_like_data_flow_query(self, lowered_query):
        if self._contains_any(
            lowered_query,
            (
                "flow from",
                "flows from",
                "back to particles",
                "back to particle",
                "grid to particles",
                "grid to particle",
                "particles to grid",
                "particle to grid",
                "field to particles",
                "field to particle",
                "transfer to particles",
                "transfer from particles",
                "interpolate to particles",
                "interpolated to particles",
                "gathered to particles",
                "gather to particles",
            ),
        ):
            return True

        mentions_grid = any(
            phrase in lowered_query
            for phrase in ("grid", "field", "mesh")
        )
        mentions_particles = any(
            phrase in lowered_query
            for phrase in ("particle", "particles")
        )
        mentions_transfer = any(
            phrase in lowered_query
            for phrase in ("flow", "transfer", "interpolate", "gather", "scatter", "back")
        )
        mentions_solver = any(
            phrase in lowered_query
            for phrase in ("poisson", "solve", "solver")
        )
        return mentions_grid and mentions_particles and (mentions_transfer or mentions_solver)

    def _looks_like_comparison_query(self, lowered_query):
        mentions_compare = any(
            phrase in lowered_query
            for phrase in (
                "tradeoff",
                "tradeoffs",
                "compare",
                "comparison",
                "different between",
                "difference between",
                "versus",
                " vs ",
            )
        )
        mentions_fft = "fft" in lowered_query
        mentions_cg = any(
            phrase in lowered_query
            for phrase in (" cg ", "cg ", " cg", "conjugate gradient", "conjugate-gradient")
        )
        mentions_poisson = "poisson" in lowered_query
        mentions_solver = "solver" in lowered_query or "solvers" in lowered_query
        return mentions_compare and mentions_fft and mentions_cg and (mentions_poisson or mentions_solver)

    def _detect_entity_target(self, lowered_query):
        # Order matters here. We want the most specific user wording to win.
        # "call chain" should not be collapsed into generic symbol-level logic,
        # and "module/folder" should outrank exact-symbol matching when both
        # appear in the same query.
        if self._contains_any(
            lowered_query,
            ("call chain", "call graph", "callgraph", "execution path", "caller", "callee"),
        ):
            return "call_chain_level"

        if self._contains_any(
            lowered_query,
            ("module", "subsystem", "folder", "package", "directory"),
        ):
            return "module_level"

        if self._contains_any(
            lowered_query,
            ("file", "header", "source file", "implementation file"),
        ):
            return "file_level"

        if self._contains_any(
            lowered_query,
            ("documentation", "docs", "readme", "section"),
        ):
            return "documentation_section_level"

        if self._contains_any(
            lowered_query,
            ("class", "struct", "function", "method", "routine", "symbol"),
        ):
            return "function_level"

        return ""

    def _build_retrieval_preferences(self, lowered_query, entity_target):
        if not entity_target:
            return {
                "entity_target": "",
                "preferred_entity_levels": (),
                "preferred_chunk_types": (),
            }

        profile = self.ENTITY_TARGET_PROFILES[entity_target]
        preferred_chunk_types = list(profile["preferred_chunk_types"])

        # Only symbol-level targets get refined by class/function/struct wording.
        # Higher-level entities such as files and modules already map 1:1 to
        # their chunk types, so extra chunk-type hints would just add noise.
        if entity_target == "function_level":
            for keyword, chunk_types in self.SYMBOL_LEVEL_CHUNK_HINTS.items():
                if keyword in lowered_query:
                    preferred_chunk_types.extend(chunk_types)

        return {
            "entity_target": entity_target,
            "preferred_entity_levels": tuple(profile["preferred_entity_levels"]),
            "preferred_chunk_types": tuple(dict.fromkeys(preferred_chunk_types)),
        }
