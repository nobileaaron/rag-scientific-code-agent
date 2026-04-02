import json
from pathlib import Path

from src.ingestion.explanation_snapshots import restore_saved_explanation
from src.prompts.prompt_templates import get_prompt_template


class FileLevelEntityBuilder:
    """Build one higher-level retrieval entity per file.

    The builder supports two modes:

    - ``symbol_aggregated``: used when the file has parsed symbols. In this
      mode we summarize the file from its symbol-level structure and previously
      generated symbol explanations.
    - ``raw_content_fallback``: used when no symbol-level structure was found.
      In this mode we rely on the raw file content plus lightweight dependency
      information.

    The main design goal is to keep file-level chunks compact enough to be
    useful to the answering LLM. Earlier versions emitted large dossiers with
    repeated symbol lines, ownership relationships, inheritance fragments, and
    raw file excerpts all at once. The current version instead produces a
    smaller "summary card" for ``symbol_aggregated`` files:

    - file identity
    - a short file summary
    - a capped list of key symbols
    - capped include/reference lists

    This keeps file-level chunks informative without letting them dominate the
    final answer prompt.
    """

    def __init__(
        self,
        llm,
        prompt_mode="file_level",
        fallback_prompt_mode="file_level_fallback",
        raw_content_char_limit=4000,
        max_key_symbols=10,
        max_include_paths=6,
        max_referenced_files=6,
        file_summary_char_limit=500,
        symbol_summary_char_limit=140,
    ):
        self.llm = llm
        self.prompt_mode = prompt_mode
        self.fallback_prompt_mode = fallback_prompt_mode
        self.prompt_template = get_prompt_template(prompt_mode)
        self.fallback_prompt_template = get_prompt_template(fallback_prompt_mode)
        self.raw_content_char_limit = raw_content_char_limit
        self.max_key_symbols = max_key_symbols
        self.max_include_paths = max_include_paths
        self.max_referenced_files = max_referenced_files
        self.file_summary_char_limit = file_summary_char_limit
        self.symbol_summary_char_limit = symbol_summary_char_limit

    def build(self, project_structure, code_entities, file_contents, saved_explanations=None):
        """Build file-level entities for every file record in the project structure.

        ``code_entities`` contains parsed symbol-level entities (functions,
        classes, structs, methods, etc.). We use those entities to decide whether
        a file should be handled in ``symbol_aggregated`` mode and to reuse any
        saved explanations already attached to the symbol-level entities.

        ``saved_explanations`` lets us restore previously generated file-level
        explanations. If restore fails, we ask the configured LLM to generate a
        new explanation from the aggregated file facts.
        """
        symbols_by_id = {
            symbol["symbol_id"]: symbol
            for symbol in project_structure.get("symbols", [])
        }
        explained_entities = {
            self._symbol_id(entity): entity
            for entity in code_entities
            if entity.get("generated_explanation_status") == "ok"
        }
        relationships = project_structure.get("relationships", {})
        file_level_entities = []
        file_records = project_structure.get("files", [])
        total_files = len(file_records)
        explained_count = 0

        for file_record in file_records:
            symbol_ids = file_record.get("symbols", [])
            symbol_records = [
                symbols_by_id[symbol_id]
                for symbol_id in symbol_ids
                if symbol_id in symbols_by_id
            ]
            raw_content = file_contents.get(file_record["path"], "")
            file_level_mode = (
                "symbol_aggregated"
                if symbol_records
                else "raw_content_fallback"
            )

            file_facts = self._build_file_facts(
                file_record,
                symbol_records,
                explained_entities,
                relationships,
                raw_content,
                file_level_mode,
            )
            prompt_mode = (
                self.prompt_mode
                if file_level_mode == "symbol_aggregated"
                else self.fallback_prompt_mode
            )
            prompt_template = (
                self.prompt_template
                if file_level_mode == "symbol_aggregated"
                else self.fallback_prompt_template
            )
            question = (
                f"Explain the role of file {file_record['file_name']} using only "
                "the provided structural facts and contained symbol summaries."
                if file_level_mode == "symbol_aggregated"
                else (
                    f"Explain the role of file {file_record['file_name']} using only "
                    "the provided whole-file facts and raw file content fallback. "
                    "No symbol-level entities were detected for this file."
                )
            )
            contained_symbol_names = self._dedupe_preserving_order(
                [symbol["symbol_name"] for symbol in symbol_records]
            )
            contained_symbol_types = self._dedupe_preserving_order(
                [
                    f"{symbol['symbol_name']} ({symbol['chunk_type']})"
                    for symbol in symbol_records
                ]
            )
            owned_symbols = sorted(
                {
                    edge["owned_symbol"]
                    for edge in relationships.get("ownership_edges", [])
                    if edge.get("file_path") == file_record["path"]
                }
            )
            inherited_base_symbols = sorted(
                {
                    edge["base_symbol"]
                    for edge in relationships.get("inheritance_edges", [])
                    if edge.get("file_path") == file_record["path"]
                }
            )

            file_level_entity = {
                "entity_id": f"file_level::{file_record['path']}",
                "entity_level": "file_level",
                "path": file_record["path"],
                "file": file_record["path"],
                "file_name": file_record["file_name"],
                "base_name": file_record["base_name"],
                "source_type": self._precise_source_type(file_record["path"]),
                "symbol_name": file_record["file_name"],
                "function_name": file_record["file_name"],
                "parent_symbol": file_record["module_key"],
                "chunk_type": "file_level",
                "entity_type": "file_level",
                "language": self._language_for_file(file_record["path"]),
                "section_path": file_record["module_key"],
                "namespace_path": "",
                "chunk_index": 1,
                "total_chunks": 1,
                "return_type": f"file:{self._precise_source_type(file_record['path'])}",
                "parameters": file_record["module_key"],
                "leading_comment": "",
                "include_paths": file_record.get("include_paths", []),
                "referenced_files": file_record.get("referenced_files", []),
                "contained_symbol_ids": symbol_ids,
                "contained_symbol_names": contained_symbol_names,
                "contained_symbol_types": contained_symbol_types,
                "owned_symbols": owned_symbols,
                "inherited_base_symbols": inherited_base_symbols,
                "module_scope": file_record["module_scope"],
                "module_path": file_record["module_path"],
                "module_key": file_record["module_key"],
                "file_level_mode": file_level_mode,
                "parsed_symbol_count": len(symbol_records),
                "raw_content_included": file_level_mode == "raw_content_fallback",
                "generated_explanation": "",
                "generated_explanation_prompt_mode": prompt_mode,
                "generated_explanation_model": getattr(self.llm, "model", "unknown"),
                "generated_explanation_status": "",
                "generated_explanation_error": "",
                "explanation_generated_from": "aggregated_file_facts",
                "code": file_facts,
            }
            if not restore_saved_explanation(
                file_level_entity,
                saved_explanations,
                entity_level="file_level",
            ):
                file_level_entity["generated_explanation"] = self.llm.generate(
                    prompt_template.format(
                        context=file_facts,
                        question=question,
                    )
                ).strip()
                file_level_entity["generated_explanation_status"] = "ok"

            file_level_entities.append(file_level_entity)
            explained_count += 1
            print(f"  explained {explained_count}/{total_files} file_level entities")

        return file_level_entities

    def save(self, file_level_entities, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(file_level_entities, file, indent=2, ensure_ascii=False)
            file.write("\n")

    def _build_file_facts(
        self,
        file_record,
        symbol_records,
        explained_entities,
        relationships,
        raw_content,
        file_level_mode,
    ):
        """Build the text payload later stored in the file-level entity ``code`` field.

        This text is the evidence package shown to:
        - the file-level explanation LLM during ingestion
        - the answering LLM later, if the file-level entity is retrieved

        The payload is intentionally mode-specific:
        - ``symbol_aggregated`` files get a compact summary card
        - ``raw_content_fallback`` files get a smaller raw-content-oriented view
        """
        include_paths = file_record.get("include_paths", [])
        referenced_files = file_record.get("referenced_files", [])
        if file_level_mode == "symbol_aggregated":
            return self._build_symbol_aggregated_file_facts(
                file_record,
                symbol_records,
                explained_entities,
                include_paths,
                referenced_files,
            )

        return self._build_raw_fallback_file_facts(
            file_record,
            include_paths,
            referenced_files,
            raw_content,
        )

    def _build_symbol_aggregated_file_facts(
        self,
        file_record,
        symbol_records,
        explained_entities,
        include_paths,
        referenced_files,
    ):
        """Build a compact summary card for files with parsed symbol structure.

        Earlier versions dumped nearly every available structural detail into the
        file facts. That made retrieval chunks noisy and repetitive. This helper
        intentionally keeps only the information most useful for downstream
        answer generation:

        - file identity
        - short file summary
        - capped key symbol list
        - capped include/reference lists
        """
        ranked_symbols = self._rank_symbols_for_file_summary(symbol_records)
        key_symbol_lines = self._build_key_symbol_lines(ranked_symbols, explained_entities)
        file_summary = self._build_file_summary(file_record, ranked_symbols, explained_entities)
        include_text = self._format_bulleted_list(include_paths, self.max_include_paths)
        referenced_text = self._format_bulleted_list(
            referenced_files,
            self.max_referenced_files,
        )

        return f"""File Path: {file_record['path']}
Module Key: {file_record['module_key']}
Source Type: {self._precise_source_type(file_record['path'])}

File Summary:
{file_summary}

Key Symbols:
{key_symbol_lines}

Include Paths:
{include_text}

Referenced Files:
{referenced_text}
"""

    def _build_raw_fallback_file_facts(
        self,
        file_record,
        include_paths,
        referenced_files,
        raw_content,
    ):
        """Build a fallback view for files without parsed symbol-level structure."""
        raw_content_block = self._format_raw_content(raw_content)
        include_text = self._format_bulleted_list(include_paths, self.max_include_paths)
        referenced_text = self._format_bulleted_list(
            referenced_files,
            self.max_referenced_files,
        )

        return f"""File Path: {file_record['path']}
File Name: {file_record['file_name']}
Base Name: {file_record['base_name']}
Source Type: {self._precise_source_type(file_record['path'])}
Module Scope: {file_record['module_scope']}
Module Path: {file_record['module_path']}
Module Key: {file_record['module_key']}
File-Level Mode: raw_content_fallback

Include Paths:
{include_text}

Referenced Files:
{referenced_text}

Raw File Content Fallback:
{raw_content_block}
"""

    def _short_explanation(self, explanation, char_limit=220):
        """Normalize whitespace and cap explanatory text to a small preview."""
        cleaned = " ".join(explanation.split())
        if not cleaned:
            return ""
        if len(cleaned) <= char_limit:
            return cleaned
        return cleaned[: max(char_limit - 3, 0)] + "..."

    def _dedupe_preserving_order(self, items):
        """Remove duplicates while keeping the first-seen ordering stable."""
        unique_items = []
        seen_items = set()

        for item in items:
            if item in seen_items:
                continue
            seen_items.add(item)
            unique_items.append(item)

        return unique_items

    def _rank_symbols_for_file_summary(self, symbol_records):
        """Order symbols by how useful they are for describing the whole file.

        The ranking is intentionally simple and explainable:
        - classes / structs first, because they often define the file's main API
        - definitions next, because they expose real behavior
        - declarations after that
        - everything else last
        """
        def rank_key(symbol):
            chunk_type = symbol.get("chunk_type", "")
            priority = self._symbol_priority(chunk_type)
            symbol_name = str(symbol.get("symbol_name", "")).lower()
            return (priority, symbol_name)

        return sorted(symbol_records, key=rank_key)

    def _symbol_priority(self, chunk_type):
        """Return a smaller-is-better ranking bucket for symbol selection."""
        if chunk_type in {"class", "struct"}:
            return 0
        if chunk_type in {"function_definition", "method_definition"}:
            return 1
        if chunk_type == "method_declaration":
            return 2
        return 3

    def _build_key_symbol_lines(self, ranked_symbols, explained_entities):
        """Render the small symbol list shown in ``symbol_aggregated`` file facts.

        Each line may include a very short symbol explanation preview when one is
        available. The list is deduplicated and capped so a large file does not
        flood the final prompt with every member and specialization.
        """
        key_symbol_lines = []
        for symbol in ranked_symbols:
            symbol_id = symbol["symbol_id"]
            explained_entity = explained_entities.get(symbol_id)
            explanation_summary = self._short_explanation(
                explained_entity.get("generated_explanation", "") if explained_entity else "",
                char_limit=self.symbol_summary_char_limit,
            )
            symbol_line = f"- {symbol['symbol_name']} ({symbol['chunk_type']})"
            if explanation_summary:
                symbol_line += f": {explanation_summary}"
            key_symbol_lines.append(symbol_line)

        key_symbol_lines = self._dedupe_preserving_order(key_symbol_lines)
        if not key_symbol_lines:
            return "- none"

        capped_lines = key_symbol_lines[: self.max_key_symbols]
        if len(key_symbol_lines) > self.max_key_symbols:
            capped_lines.append(
                f"- [additional symbols omitted: {len(key_symbol_lines) - self.max_key_symbols}]"
            )
        return "\n".join(capped_lines)

    def _build_file_summary(self, file_record, ranked_symbols, explained_entities):
        """Synthesize a short file summary from the best available symbol summaries.

        We prefer existing symbol-level explanations because they are already the
        most semantically dense descriptions available. If none exist, we fall
        back to a lightweight structural summary derived from symbol names and
        types. This avoids forcing raw file content into the file-level facts
        when symbol structure is already available.
        """
        summary_fragments = []
        for symbol in ranked_symbols:
            explained_entity = explained_entities.get(symbol["symbol_id"])
            if explained_entity is None:
                continue
            explanation_summary = self._short_explanation(
                explained_entity.get("generated_explanation", ""),
                char_limit=180,
            )
            if not explanation_summary:
                continue
            summary_fragments.append(explanation_summary)
            if len(summary_fragments) >= 3:
                break

        if summary_fragments:
            summary_text = " ".join(self._dedupe_preserving_order(summary_fragments))
            return self._short_explanation(
                summary_text,
                char_limit=self.file_summary_char_limit,
            )

        symbol_descriptions = self._dedupe_preserving_order(
            [
                f"{symbol['symbol_name']} ({symbol['chunk_type']})"
                for symbol in ranked_symbols[: self.max_key_symbols]
            ]
        )
        if symbol_descriptions:
            summary_text = (
                f"{self._precise_source_type(file_record['path']).capitalize()} file in module "
                f"{file_record['module_key']} with key symbols: "
                + ", ".join(symbol_descriptions)
                + "."
            )
            return self._short_explanation(
                summary_text,
                char_limit=self.file_summary_char_limit,
            )

        return (
            f"{self._precise_source_type(file_record['path']).capitalize()} file in module "
            f"{file_record['module_key']}."
        )

    def _format_bulleted_list(self, items, max_items):
        """Render a deduplicated, capped bullet list with an omission marker."""
        unique_items = self._dedupe_preserving_order([str(item) for item in items if str(item).strip()])
        if not unique_items:
            return "- none"

        capped_items = unique_items[:max_items]
        lines = [f"- {item}" for item in capped_items]
        if len(unique_items) > max_items:
            lines.append(f"- [additional items omitted: {len(unique_items) - max_items}]")
        return "\n".join(lines)

    def _precise_source_type(self, file_path):
        suffix = Path(file_path).suffix.lower()
        if suffix == ".cpp":
            return "cpp"
        if suffix in {".h", ".hpp"}:
            return "header"
        return "documentation"

    def _language_for_file(self, file_path):
        suffix = Path(file_path).suffix.lower()
        if suffix in {".cpp", ".h", ".hpp"}:
            return "cpp"
        if suffix == ".md":
            return "markdown"
        if suffix == ".rst":
            return "rst"
        return "text"

    def _symbol_id(self, entity):
        file_path = entity.get("path", entity.get("file", ""))
        symbol_name = entity.get("symbol_name", entity.get("function_name", ""))
        parent_symbol = entity.get("parent_symbol", entity.get("class_name", ""))
        entity_type = entity.get("entity_type", entity.get("chunk_type", "entity"))
        return f"{file_path}::{parent_symbol}::{symbol_name}::{entity_type}"

    def _format_raw_content(self, raw_content):
        if not raw_content:
            return "- none"

        normalized = raw_content.strip()
        if len(normalized) <= self.raw_content_char_limit:
            return normalized

        return (
            normalized[: self.raw_content_char_limit]
            + f"\n\n[truncated to first {self.raw_content_char_limit} characters]"
        )
