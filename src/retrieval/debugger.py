class RetrievalDebugger:
    def __init__(self, enabled=False, preview_chars=80, max_candidates=10):
        self.enabled = enabled
        self.preview_chars = preview_chars
        self.max_candidates = max_candidates

    def print_report(self, query, diagnostics, selected_chunks=None):
        if not self.enabled or not diagnostics:
            return

        print("\n=== Retrieval Debug Report ===")
        print(f"Query: {query}")
        print(f"Candidate pool size: {diagnostics.get('candidate_count', 0)}")
        print(f"Supplementary chunk count: {diagnostics.get('supplementary_chunk_count', 0)}")
        print(
            f"Target-aligned candidate count: {diagnostics.get('target_aligned_candidate_count', 0)}"
        )
        print(f"Primary selected count: {diagnostics.get('primary_selected_count', 0)}")
        print(
            f"Primary score-filtered count: {diagnostics.get('primary_score_filtered_count', 0)}"
        )

        exact_filenames = diagnostics.get("exact_filenames", [])
        if exact_filenames:
            print(f"Exact filenames detected: {', '.join(exact_filenames)}")

        exact_symbols = diagnostics.get("exact_symbols", [])
        if exact_symbols:
            print(f"Exact symbols detected: {', '.join(exact_symbols)}")

        query_intent = diagnostics.get("query_intent", "")
        if query_intent:
            print(f"Query intent: {query_intent}")

        query_intent_reasons = diagnostics.get("query_intent_reasons", [])
        if query_intent_reasons:
            print(f"Query intent reasons: {', '.join(query_intent_reasons)}")

        entity_target = diagnostics.get("entity_target", "")
        if entity_target:
            print(f"Explicit entity target: {entity_target}")

        preferred_entity_levels = diagnostics.get("preferred_entity_levels", [])
        if preferred_entity_levels:
            print(f"Preferred entity levels: {', '.join(preferred_entity_levels)}")

        preferred_chunk_types = diagnostics.get("preferred_chunk_types", [])
        if preferred_chunk_types:
            print(f"Preferred chunk types: {', '.join(preferred_chunk_types)}")

        primary_score_gate = diagnostics.get("primary_score_gate", {})
        if primary_score_gate:
            print(
                "Primary score gate: "
                f"top={primary_score_gate.get('top_score', 0.0):.3f} "
                f"relative_floor={primary_score_gate.get('relative_floor', 0.0):.2f} "
                f"relative_floor_score={primary_score_gate.get('relative_floor_score', 0.0):.3f} "
                f"absolute_floor={primary_score_gate.get('absolute_floor', 0.0):.3f} "
                f"gap_threshold={primary_score_gate.get('gap_threshold', 0.0):.3f} "
                f"stop_reason={primary_score_gate.get('stop_reason', 'unknown')}"
            )

        structural_mode = diagnostics.get("structural_expansion_mode", "")
        if structural_mode:
            print(f"Structural expansion mode: {structural_mode}")

        structural_count = diagnostics.get("structural_expansion_count", 0)
        if structural_count:
            print(f"Structural expansion count: {structural_count}")

        supplementary_files = diagnostics.get("supplementary_files", [])
        if supplementary_files:
            print(f"Supplementary files: {', '.join(supplementary_files)}")

        query_tokens = diagnostics.get("query_tokens", [])
        if query_tokens:
            print(f"Query tokens: {', '.join(query_tokens)}")

        print("\nTop reranked candidates:")
        for rank, candidate in enumerate(
            diagnostics.get("reranked_candidates", [])[: self.max_candidates],
            start=1,
        ):
            chunk = candidate["chunk"]
            preview = chunk.get("code", "")[: self.preview_chars].replace("\n", " ")
            if len(chunk.get("code", "")) > self.preview_chars:
                preview += "..."

            print(
                f"{rank}. combined={candidate['combined_score']:.3f} "
                f"semantic={candidate['semantic_score']:.3f} "
                f"target={candidate.get('entity_target_score', 0.0):.3f} "
                f"metadata={candidate['metadata_score']:.3f}"
            )
            print(
                f"   file={chunk.get('file_name', '')} "
                f"source={chunk.get('source_type', '')} "
                f"symbol={chunk.get('symbol_name', chunk.get('function_name', ''))}"
            )
            print(f"   path={chunk.get('path', chunk.get('file', ''))}")
            print(f"   preview={preview}")

        filtered_candidates = diagnostics.get("primary_score_filtered_candidates", [])
        if filtered_candidates:
            print("\nPrimary candidates dropped by score gate:")
            for rank, candidate in enumerate(
                filtered_candidates[: self.max_candidates],
                start=1,
            ):
                chunk = candidate["chunk"]
                preview = chunk.get("code", "")[: self.preview_chars].replace("\n", " ")
                if len(chunk.get("code", "")) > self.preview_chars:
                    preview += "..."

                print(
                    f"{rank}. combined={candidate['combined_score']:.3f} "
                    f"semantic={candidate['semantic_score']:.3f} "
                    f"target={candidate.get('entity_target_score', 0.0):.3f} "
                    f"metadata={candidate['metadata_score']:.3f}"
                )
                print(
                    f"   file={chunk.get('file_name', '')} "
                    f"source={chunk.get('source_type', '')} "
                    f"symbol={chunk.get('symbol_name', chunk.get('function_name', ''))}"
                )
                print(f"   path={chunk.get('path', chunk.get('file', ''))}")
                print(f"   preview={preview}")

        if selected_chunks:
            self._print_selected_chunks(selected_chunks)

        print("=== End Debug Report ===\n")

    def print_prompt_report(self, prompt_package):
        if not self.enabled or not prompt_package:
            return

        metadata = prompt_package.get("metadata", {})
        messages = prompt_package.get("messages", [])
        prompt_text = prompt_package.get("text", "")

        print("\n=== LLM Prompt Debug Report ===")
        print(f"Model: {metadata.get('model', 'unknown')}")
        print(f"Prompt mode: {metadata.get('prompt_mode', 'unknown')}")
        print(f"Prompt signature: {metadata.get('prompt_signature', 'unknown')}")
        print(f"Message count: {metadata.get('message_count', len(messages))}")
        print(f"Selected chunk count: {metadata.get('selected_chunk_count', 0)}")
        print(f"Raw selected chunk count: {metadata.get('raw_selected_chunk_count', 0)}")
        print(f"Dropped chunk count: {metadata.get('dropped_chunk_count', 0)}")
        print(f"Context size: {metadata.get('context_char_count', 0)} chars")
        print(f"Context lines: {metadata.get('context_line_count', 0)}")
        print(f"Question size: {metadata.get('question_char_count', 0)} chars")

        chunk_paths = metadata.get("chunk_paths", [])
        if chunk_paths:
            print("Chunk paths:")
            for chunk_path in chunk_paths:
                print(f"  - {chunk_path}")

        print("\nRendered message summary:")
        for message_metadata, message in zip(metadata.get("messages", []), messages):
            print(
                f"[{message_metadata.get('index', '?')}] role={message_metadata.get('role', 'unknown')} "
                f"chars={message_metadata.get('char_count', len(message.get('content', '')))} "
                f"lines={message_metadata.get('line_count', len(message.get('content', '').splitlines()))}"
            )

        print("\nSerialized prompt sent to the LLM:")
        print(prompt_text)
        print("=== End LLM Prompt Debug Report ===\n")

    def _print_selected_chunks(self, chunks):
        print("\nFinal retrieved context:")

        files_by_role = {}
        for chunk in chunks:
            retrieval_role = chunk.get("retrieval_role", "unknown")
            file_path = chunk.get("path", chunk.get("file", ""))
            if file_path:
                files_by_role.setdefault(retrieval_role, [])
                if file_path not in files_by_role[retrieval_role]:
                    files_by_role[retrieval_role].append(file_path)

        if files_by_role:
            print("Retrieved files by role:")
            for retrieval_role, file_paths in files_by_role.items():
                print(f"  {retrieval_role}:")
                for file_path in file_paths:
                    print(f"    - {file_path}")

        for rank, chunk in enumerate(chunks, start=1):
            retrieval_role = chunk.get("retrieval_role", "primary")
            source_type = chunk.get("source_type", "unknown")
            chunk_type = chunk.get("chunk_type", chunk.get("entity_type", ""))
            entity_level = chunk.get("entity_level", "")
            symbol_name = chunk.get("symbol_name", chunk.get("function_name", ""))
            parent_symbol = chunk.get("parent_symbol", "")
            file_path = chunk.get("path", chunk.get("file", ""))
            language = chunk.get("language", "")
            return_type = chunk.get("return_type", "")
            section_path = chunk.get("section_path", chunk.get("parameters", ""))
            chunk_index = chunk.get("chunk_index", 1)
            total_chunks = chunk.get("total_chunks", 1)
            explanation_status = chunk.get("generated_explanation_status", "")
            expansion_reason = chunk.get("expansion_reason", "")
            include_paths = chunk.get("include_paths", [])
            referenced_files = chunk.get("referenced_files", [])
            preview = chunk.get("code", "")[: self.preview_chars].replace("\n", " ")
            if len(chunk.get("code", "")) > self.preview_chars:
                preview += "..."

            print(
                f"\n{rank}. role={retrieval_role} "
                f"source={source_type} chunk_type={chunk_type} entity_level={entity_level}"
            )
            print(f"   symbol={symbol_name} parent={parent_symbol or 'none'}")
            print(f"   path={file_path}")
            print(f"   language={language} return_type={return_type}")
            print(f"   section_path={section_path} chunk={chunk_index}/{total_chunks}")
            print(f"   explanation_status={explanation_status or 'none'}")
            if expansion_reason:
                print(f"   expansion_reason={expansion_reason}")
            if include_paths:
                print(f"   include_paths={', '.join(include_paths)}")
            if referenced_files:
                print(f"   referenced_files={', '.join(referenced_files)}")
            print(f"   preview={preview}")
