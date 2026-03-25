import json
from pathlib import Path

from src.prompts.prompt_templates import get_prompt_template


class FileLevelEntityBuilder:
    def __init__(
        self,
        llm,
        prompt_mode="file_level",
        fallback_prompt_mode="file_level_fallback",
        raw_content_char_limit=4000,
    ):
        self.llm = llm
        self.prompt_mode = prompt_mode
        self.fallback_prompt_mode = fallback_prompt_mode
        self.prompt_template = get_prompt_template(prompt_mode)
        self.fallback_prompt_template = get_prompt_template(fallback_prompt_mode)
        self.raw_content_char_limit = raw_content_char_limit

    def build(self, project_structure, code_entities, file_contents):
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

        for file_record in project_structure.get("files", []):
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
            explanation = self.llm.generate(
                prompt_template.format(
                    context=file_facts,
                    question=question,
                )
            ).strip()

            contained_symbol_names = [symbol["symbol_name"] for symbol in symbol_records]
            contained_symbol_types = [
                f"{symbol['symbol_name']} ({symbol['chunk_type']})"
                for symbol in symbol_records
            ]
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

            file_level_entities.append(
                {
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
                    "generated_explanation": explanation,
                    "generated_explanation_prompt_mode": prompt_mode,
                    "generated_explanation_model": getattr(self.llm, "model", "unknown"),
                    "generated_explanation_status": "ok",
                    "generated_explanation_error": "",
                    "explanation_generated_from": "aggregated_file_facts",
                    "code": file_facts,
                }
            )

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
        include_paths = file_record.get("include_paths", [])
        referenced_files = file_record.get("referenced_files", [])
        ownership_edges = [
            edge
            for edge in relationships.get("ownership_edges", [])
            if edge.get("file_path") == file_record["path"]
        ]
        inheritance_edges = [
            edge
            for edge in relationships.get("inheritance_edges", [])
            if edge.get("file_path") == file_record["path"]
        ]

        symbol_lines = []
        for symbol in symbol_records:
            symbol_id = symbol["symbol_id"]
            explained_entity = explained_entities.get(symbol_id)
            explanation_summary = self._short_explanation(
                explained_entity.get("generated_explanation", "") if explained_entity else ""
            )
            symbol_line = (
                f"- {symbol['symbol_name']} ({symbol['chunk_type']})"
                f" parent={symbol.get('parent_symbol', '') or 'none'}"
            )
            if explanation_summary:
                symbol_line += f" | summary={explanation_summary}"
            symbol_lines.append(symbol_line)

        ownership_lines = [
            f"- {edge['owner_symbol']} owns {edge['owned_symbol']}"
            for edge in ownership_edges
        ]
        inheritance_lines = [
            f"- {edge['derived_symbol']} inherits {edge['base_symbol']}"
            for edge in inheritance_edges
        ]
        raw_content_block = self._format_raw_content(raw_content)

        include_text = "\n".join(f"- {include_path}" for include_path in include_paths) or "- none"
        referenced_text = (
            "\n".join(f"- {file_name}" for file_name in referenced_files) or "- none"
        )
        symbol_text = "\n".join(symbol_lines) or "- none"
        ownership_text = "\n".join(ownership_lines) or "- none"
        inheritance_text = "\n".join(inheritance_lines) or "- none"

        return f"""File Path: {file_record['path']}
File Name: {file_record['file_name']}
Base Name: {file_record['base_name']}
Source Type: {self._precise_source_type(file_record['path'])}
Module Scope: {file_record['module_scope']}
Module Path: {file_record['module_path']}
Module Key: {file_record['module_key']}
File-Level Mode: {file_level_mode}

Contained Symbols:
{symbol_text}

Include Paths:
{include_text}

Referenced Files:
{referenced_text}

Ownership Relationships:
{ownership_text}

Inheritance Relationships:
{inheritance_text}

Raw File Content Fallback:
{raw_content_block}
"""

    def _short_explanation(self, explanation):
        cleaned = " ".join(explanation.split())
        if not cleaned:
            return ""
        if len(cleaned) <= 220:
            return cleaned
        return cleaned[:217] + "..."

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
