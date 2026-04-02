# 1. Takes User query
# 2. Retrieves top-k chunks
# 3. Builds a prompt 
# 4. Calls the LLM
# 5. Returns the answer

#import Ollama -> dont need Ollama directly now we use llm_wrapper

import re

from src.prompts.prompt_templates import (
    get_prompt_template_signature_from_template,
    render_prompt_messages,
    render_prompt_text_from_messages,
)


class LLMAgent:
    # These weights tune the final-context filter that runs after retrieval.
    # The goal is not to change retrieval itself, but to avoid sending obviously
    # weak chunks to the answering LLM when a better nearby chunk already covers
    # the same local concept (same file, same symbol, or a nearby file-level
    # expansion).
    FINAL_CONTEXT_SCORE_WEIGHTS = {
        "generated_explanation": 4,
        "leading_comment": 2,
        "include_paths": 1,
        "referenced_files": 1,
        "high_level_context": 3,
        "rich_code": 2,
        "medium_code": 1,
        "low_information_status": -4,
        "trivial_declaration": -3,
    }

    # A chunk at or below this score is considered weak enough to be a drop
    # candidate, but only if a clearly stronger contextual neighbor exists.
    FINAL_CONTEXT_LOW_SCORE_THRESHOLD = 0

    # A stronger neighbor must beat the weak chunk by at least this margin
    # before we suppress the weak chunk from the final prompt.
    FINAL_CONTEXT_BETTER_EVIDENCE_MARGIN = 3

    # This is a floor on what counts as genuinely useful replacement evidence.
    FINAL_CONTEXT_MIN_BETTER_EVIDENCE_SCORE = 2

    TRIVIAL_DECLARATION_PATTERNS = (
        re.compile(r"^\s*(class|struct)\s+[A-Za-z_][A-Za-z0-9_:<>]*\s*\{\s*\}\s*;?\s*$"),
        re.compile(r"^\s*enum(\s+class)?\s+[A-Za-z_][A-Za-z0-9_:<>]*\s*\{\s*\}\s*;?\s*$"),
    )

    # Only these chunk types get a ``_chunk`` suffix when a single parsed symbol
    # had to be split into multiple retrieval chunks. This keeps the label honest
    # for the answering LLM without changing the stored underlying chunk type.
    SPLITTABLE_CHUNK_TYPES = {
        "function_definition",
        "method_definition",
        "method_declaration",
        "class",
        "struct",
        "section",
        "paragraph",
        "code_block",
    }

    def __init__(
        self,
        retriever,
        llm,
        prompt_type,
        retrieval_debugger=None,
        prompt_mode="unknown",
    ):
        self.retriever = retriever
        self.llm = llm
        self.prompt_template = prompt_type
        self.retrieval_debugger = retrieval_debugger
        self.prompt_mode = prompt_mode
        self.prompt_signature = get_prompt_template_signature_from_template(prompt_type)


    def build_context(self, chunks):
        context_sections = []

        for rank, chunk in enumerate(chunks, start=1):
            retrieval_role = chunk.get("retrieval_role", "primary")
            symbol_name = chunk.get("symbol_name", chunk.get("function_name", ""))
            parent_symbol = chunk.get("parent_symbol", "")
            chunk_type = chunk.get("chunk_type", chunk.get("entity_type", ""))
            entity_level = chunk.get("entity_level", "")
            file_path = chunk.get("path", chunk.get("file", ""))
            section_path = chunk.get("section_path", "")
            parameters = chunk.get("parameters", "")
            chunk_index = chunk.get("chunk_index", 1)
            total_chunks = chunk.get("total_chunks", 1)
            leading_comment = chunk.get("leading_comment", "")
            generated_explanation = chunk.get("generated_explanation", "")
            generated_explanation_status = chunk.get("generated_explanation_status", "")
            expansion_reason = chunk.get("expansion_reason", "")
            include_paths = chunk.get("include_paths", [])
            referenced_files = chunk.get("referenced_files", [])
            normalized_symbol_name = str(symbol_name or "").strip()
            normalized_parent_symbol = str(parent_symbol or "").strip()
            display_parent_symbol = normalized_parent_symbol
            if normalized_parent_symbol == normalized_symbol_name:
                display_parent_symbol = ""
            explanation_text = generated_explanation.strip() if generated_explanation else ""
            expansion_text = expansion_reason.strip() if expansion_reason else ""
            include_text = ", ".join(include_paths) if include_paths else ""
            referenced_files_text = ", ".join(referenced_files) if referenced_files else ""
            return_type = chunk.get("return_type", "")
            display_entity_level = self._display_entity_level(entity_level)
            display_chunk_type = self._display_chunk_type(
                chunk_type,
                chunk_index=chunk_index,
                total_chunks=total_chunks,
            )
            display_section_or_parameters = self._display_section_or_parameters(
                section_path=section_path,
                parameters=parameters,
                symbol_name=symbol_name,
                parent_symbol=parent_symbol,
                file_path=file_path,
            )

            chunk_lines = [
                f"### Retrieved Chunk {rank}",
                f"Retrieval Role: {retrieval_role}",
                f"Entity Level: {display_entity_level}",
                f"Symbol: {symbol_name or 'unknown'}",
                f"Path: {file_path or 'unknown'}",
            ]
            if self._should_show_chunk_type(
                display_chunk_type=display_chunk_type,
                display_entity_level=display_entity_level,
            ):
                chunk_lines.append(f"Chunk Type: {display_chunk_type}")
            if self._should_show_return_type(
                chunk_type=chunk_type,
                return_type=return_type,
            ):
                chunk_lines.append(f"Return Type: {return_type}")
            if display_section_or_parameters:
                chunk_lines.append(
                    f"Parameters / Section Path: {display_section_or_parameters}"
                )
            if chunk_index != 1 or total_chunks != 1:
                chunk_lines.append(f"Chunk Position: {chunk_index}/{total_chunks}")
            if expansion_text:
                chunk_lines.append(f"Expansion Reason: {expansion_text}")
            if display_parent_symbol:
                chunk_lines.append(f"Parent Symbol: {display_parent_symbol}")
            if leading_comment:
                chunk_lines.extend(
                    [
                        "Leading Comment:",
                        leading_comment,
                    ]
                )
            if explanation_text:
                chunk_lines.extend(
                    [
                        "Generated Explanation:",
                        explanation_text,
                    ]
                )
            if include_text:
                chunk_lines.append(f"Include Paths: {include_text}")
            if referenced_files_text:
                chunk_lines.append(f"Referenced Files: {referenced_files_text}")
            chunk_lines.extend(
                [
                    "Content:",
                    chunk.get("code", ""),
                ]
            )
            context_sections.append("\n".join(chunk_lines))

        return "\n\n".join(context_sections)

    def _filter_final_chunks(self, chunks):
        """Drop weak final-context chunks only when stronger nearby evidence exists.

        Retrieval still decides which chunks are relevant. This method only trims
        the subset that gets shown to the answering LLM. The main target is
        low-information declarations such as ``class FFT {}`` with no explanation,
        no comment, and no structural hints. Those chunks may still be useful as
        retrieval waypoints, but they usually do not help the final answer if a
        richer chunk from the same local context is already present.
        """
        evaluated_chunks = [
            {
                "chunk": chunk,
                "quality": self._evaluate_chunk_for_final_context(chunk),
            }
            for chunk in chunks
        ]

        filtered_chunks = []
        dropped_chunk_count = 0
        for current in evaluated_chunks:
            if self._should_drop_from_final_context(current, evaluated_chunks):
                dropped_chunk_count += 1
                continue
            filtered_chunks.append(current["chunk"])

        if not filtered_chunks and chunks:
            # Never return an empty context when retrieval succeeded. If
            # everything looks weak, keep the original set rather than risk
            # deleting the only available evidence.
            return chunks, {
                "raw_chunk_count": len(chunks),
                "final_chunk_count": len(chunks),
                "dropped_chunk_count": 0,
            }

        return filtered_chunks, {
            "raw_chunk_count": len(chunks),
            "final_chunk_count": len(filtered_chunks),
            "dropped_chunk_count": dropped_chunk_count,
        }

    def _evaluate_chunk_for_final_context(self, chunk):
        """Return a scored quality summary used by the final-context filter.

        The returned dictionary is intentionally explicit so the scoring system is
        easy to inspect and tune later. A higher score means the chunk is more
        useful as direct evidence for the answering LLM.
        """
        weights = self.FINAL_CONTEXT_SCORE_WEIGHTS
        generated_explanation = str(chunk.get("generated_explanation", "") or "").strip()
        leading_comment = str(chunk.get("leading_comment", "") or "").strip()
        include_paths = chunk.get("include_paths", []) or []
        referenced_files = chunk.get("referenced_files", []) or []
        code = str(chunk.get("code", "") or "")
        code_length = len(code.strip())
        entity_level = str(chunk.get("entity_level", "") or "")
        generated_explanation_status = str(
            chunk.get("generated_explanation_status", "") or ""
        ).strip()
        is_trivial_declaration = self._is_trivial_declaration(code)
        is_high_level_context = entity_level in {
            "file_level",
            "module_level",
            "call_chain_level",
        }

        score = 0
        if generated_explanation:
            score += weights["generated_explanation"]
        if leading_comment:
            score += weights["leading_comment"]
        if include_paths:
            score += weights["include_paths"]
        if referenced_files:
            score += weights["referenced_files"]
        if is_high_level_context:
            score += weights["high_level_context"]
        if code_length >= 400:
            score += weights["rich_code"]
        elif code_length >= 120:
            score += weights["medium_code"]
        if generated_explanation_status == "skipped_low_information":
            score += weights["low_information_status"]
        if is_trivial_declaration:
            score += weights["trivial_declaration"]

        return {
            "score": score,
            "generated_explanation_status": generated_explanation_status,
            "has_generated_explanation": bool(generated_explanation),
            "has_leading_comment": bool(leading_comment),
            "has_include_paths": bool(include_paths),
            "has_referenced_files": bool(referenced_files),
            "is_high_level_context": is_high_level_context,
            "is_trivial_declaration": is_trivial_declaration,
            "code_length": code_length,
        }

    def _display_entity_level(self, entity_level):
        normalized = str(entity_level or "").strip()
        if normalized == "function_level":
            return "symbol_level"
        return normalized or "unknown"

    def _should_show_chunk_type(self, display_chunk_type, display_entity_level):
        normalized_chunk_type = str(display_chunk_type or "").strip()
        normalized_entity_level = str(display_entity_level or "").strip()
        if not normalized_chunk_type:
            return False
        return normalized_chunk_type != normalized_entity_level

    def _should_show_return_type(self, chunk_type, return_type):
        normalized_return_type = str(return_type or "").strip()
        normalized_chunk_type = str(chunk_type or "").strip()
        if not normalized_return_type:
            return False
        return normalized_chunk_type in {
            "function_definition",
            "function_declaration",
            "method_definition",
            "method_declaration",
        }

    def _display_chunk_type(self, chunk_type, chunk_index, total_chunks):
        normalized = str(chunk_type or "").strip()
        if not normalized:
            normalized = "unknown"
        if total_chunks > 1 and normalized in self.SPLITTABLE_CHUNK_TYPES:
            return f"{normalized}_chunk"
        return normalized

    def _display_section_or_parameters(
        self,
        section_path,
        parameters,
        symbol_name,
        parent_symbol,
        file_path,
    ):
        """Choose the most informative structural/signature field for display.

        ``section_path`` is often useful for documentation or nested symbol
        hierarchy, but for many code chunks it degenerates into the same text as
        the symbol or parent symbol (for example ``FFT`` for a class chunk). In
        those cases we try ``parameters`` as a fallback so method signatures
        still show up when they add real value.
        """
        for candidate in (section_path, parameters):
            if self._is_informative_context_value(
                candidate,
                symbol_name=symbol_name,
                parent_symbol=parent_symbol,
                file_path=file_path,
            ):
                return str(candidate).strip()
        return ""

    def _is_informative_context_value(
        self,
        value,
        symbol_name,
        parent_symbol,
        file_path,
    ):
        normalized_value = str(value or "").strip()
        if not normalized_value:
            return False

        normalized_value_lower = normalized_value.lower()
        if normalized_value_lower in {"none", "unknown"}:
            return False

        normalized_symbol = str(symbol_name or "").strip().lower()
        normalized_parent = str(parent_symbol or "").strip().lower()
        normalized_file_path = str(file_path or "").strip().lower()

        if normalized_value_lower == normalized_symbol and normalized_symbol:
            return False
        if normalized_value_lower == normalized_parent and normalized_parent:
            return False
        if normalized_value_lower == normalized_file_path and normalized_file_path:
            return False

        return True

    def _should_drop_from_final_context(self, current, evaluated_chunks):
        quality = current["quality"]
        if quality["score"] > self.FINAL_CONTEXT_LOW_SCORE_THRESHOLD:
            return False

        if (
            quality["generated_explanation_status"] != "skipped_low_information"
            and not quality["is_trivial_declaration"]
        ):
            return False

        current_chunk = current["chunk"]
        current_score = quality["score"]
        for candidate in evaluated_chunks:
            if candidate is current:
                continue
            if not self._chunks_share_local_context(current_chunk, candidate["chunk"]):
                continue

            candidate_score = candidate["quality"]["score"]
            if candidate_score < self.FINAL_CONTEXT_MIN_BETTER_EVIDENCE_SCORE:
                continue
            if candidate_score < current_score + self.FINAL_CONTEXT_BETTER_EVIDENCE_MARGIN:
                continue
            return True

        return False

    def _chunks_share_local_context(self, left_chunk, right_chunk):
        left_path = str(left_chunk.get("path", left_chunk.get("file", "")) or "")
        right_path = str(right_chunk.get("path", right_chunk.get("file", "")) or "")
        if not left_path or not right_path:
            return False

        if left_path == right_path:
            left_symbol = self._normalized_symbol(left_chunk)
            right_symbol = self._normalized_symbol(right_chunk)
            left_parent = self._normalized_parent_symbol(left_chunk)
            right_parent = self._normalized_parent_symbol(right_chunk)
            if left_symbol and right_symbol and left_symbol == right_symbol:
                return True
            if left_parent and right_parent and left_parent == right_parent:
                return True
            if self._is_high_level_context_chunk(left_chunk) or self._is_high_level_context_chunk(
                right_chunk
            ):
                return True

        return False

    def _is_high_level_context_chunk(self, chunk):
        return str(chunk.get("entity_level", "") or "") in {
            "file_level",
            "module_level",
            "call_chain_level",
        }

    def _normalized_symbol(self, chunk):
        symbol_name = chunk.get("symbol_name", chunk.get("function_name", ""))
        return str(symbol_name or "").strip().lower()

    def _normalized_parent_symbol(self, chunk):
        parent_symbol = str(chunk.get("parent_symbol", "") or "").strip().lower()
        symbol_name = self._normalized_symbol(chunk)
        if parent_symbol == symbol_name:
            return ""
        return parent_symbol

    def _is_trivial_declaration(self, code):
        stripped_code = str(code or "").strip()
        if not stripped_code:
            return True
        for pattern in self.TRIVIAL_DECLARATION_PATTERNS:
            if pattern.match(stripped_code):
                return True
        return False

    def _build_prompt_package(self, query, chunks, context, filter_summary=None):
        prompt_messages = render_prompt_messages(
            self.prompt_template,
            context=context,
            question=query,
        )
        prompt_text = render_prompt_text_from_messages(prompt_messages)
        prompt_metadata = {
            "model": getattr(self.llm, "model", "unknown"),
            "prompt_mode": self.prompt_mode,
            "prompt_signature": self.prompt_signature,
            "message_count": len(prompt_messages),
            "selected_chunk_count": len(chunks),
            "context_char_count": len(context),
            "context_line_count": len(context.splitlines()),
            "question_char_count": len(query),
            "raw_selected_chunk_count": (
                filter_summary.get("raw_chunk_count", len(chunks))
                if filter_summary is not None
                else len(chunks)
            ),
            "dropped_chunk_count": (
                filter_summary.get("dropped_chunk_count", 0)
                if filter_summary is not None
                else 0
            ),
            "messages": [
                {
                    "index": index,
                    "role": message["role"],
                    "char_count": len(message["content"]),
                    "line_count": len(message["content"].splitlines()),
                }
                for index, message in enumerate(prompt_messages, start=1)
            ],
            "chunk_paths": [
                chunk.get("path", chunk.get("file", ""))
                for chunk in chunks
                if chunk.get("path", chunk.get("file", ""))
            ],
        }
        return {
            "messages": prompt_messages,
            "text": prompt_text,
            "metadata": prompt_metadata,
        }

    def answer(self, query, k=5):
        # 1 retrieve relevant chunks
        retrieval_result = self.retriever.retrieve_with_diagnostics(query, k)
        chunks, filter_summary = self._filter_final_chunks(retrieval_result["chunks"])
        if self.retrieval_debugger is not None:
            self.retrieval_debugger.print_report(
                query,
                retrieval_result["diagnostics"],
                selected_chunks=chunks,
            )

        # 2 build context for LLM
        context = self.build_context(chunks)

        # Import Prompt from prompt folder -> what is the system, what should it do?
        prompt_package = self._build_prompt_package(
            query,
            chunks,
            context,
            filter_summary=filter_summary,
        )

        if self.retrieval_debugger is not None:
            self.retrieval_debugger.print_prompt_report(prompt_package)

        #return response["message"]["content"]
        return self.llm.generate(prompt_package)
