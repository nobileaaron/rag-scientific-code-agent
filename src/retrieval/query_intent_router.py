class QueryIntentRouter:
    # adjust intent-to-expansion mapping here later if retrieval feels too narrow or too broad.
    INTENT_PROFILES = {
        "location_lookup": {
            "structural_mode": "mode_1_minimal",
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

    def route(self, query, exact_filenames=None, exact_symbols=None):
        exact_filenames = exact_filenames or set()
        exact_symbols = exact_symbols or set()
        lowered = query.lower()
        reasons = []

        if self._contains_any(
            lowered,
            ("where", "find", "located", "implemented", "defined"),
        ):
            reasons.append("matched_location_keywords")
            return self._result("location_lookup", reasons)

        if self._contains_any(
            lowered,
            ("how does", "workflow", "pipeline", "process", "compute", "calculation", "call chain"),
        ):
            reasons.append("matched_workflow_keywords")
            return self._result("workflow_explanation", reasons)

        if self._contains_any(
            lowered,
            ("module", "subsystem", "folder", "package", "directory"),
        ):
            reasons.append("matched_module_keywords")
            return self._result("module_overview", reasons)

        if exact_filenames:
            reasons.append("detected_exact_filename")
            return self._result("file_purpose", reasons)

        if exact_symbols:
            reasons.append("detected_exact_symbol")
            return self._result("symbol_explanation", reasons)

        reasons.append("fell_back_to_default")
        return self._result("default", reasons)

    def _result(self, intent, reasons):
        profile = self.INTENT_PROFILES[intent]
        return {
            "intent": intent,
            "structural_mode": profile["structural_mode"],
            "reasons": reasons,
        }

    def _contains_any(self, lowered_query, phrases):
        return any(phrase in lowered_query for phrase in phrases)
