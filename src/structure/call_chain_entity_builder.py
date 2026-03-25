import json
from pathlib import Path

from src.prompts.prompt_templates import get_prompt_template


class CallChainEntityBuilder:
    def __init__(self, llm, prompt_mode="call_chain", summary_char_limit=220):
        self.llm = llm
        self.prompt_mode = prompt_mode
        self.prompt_template = get_prompt_template(prompt_mode)
        self.summary_char_limit = summary_char_limit
        self.callable_types = {
            "function_definition",
            "method_definition",
            "method_declaration",
        }

    def build(self, project_structure, code_entities, file_level_entities, module_level_entities):
        symbol_records = project_structure.get("symbols", [])
        call_edges = project_structure.get("relationships", {}).get("call_edges", [])
        symbols_by_id = {
            symbol["symbol_id"]: symbol
            for symbol in symbol_records
        }
        explained_entities = {
            self._symbol_id(entity): entity
            for entity in code_entities
            if entity.get("generated_explanation_status") == "ok"
        }
        file_level_by_path = {
            entity["path"]: entity
            for entity in file_level_entities
        }
        module_level_by_key = {
            entity["module_key"]: entity
            for entity in module_level_entities
        }
        outgoing_by_caller = {}
        incoming_by_callee = {}

        for edge in call_edges:
            outgoing_by_caller.setdefault(edge.get("caller_symbol_id", ""), []).append(edge)
            callee_symbol_id = edge.get("callee_symbol_id", "")
            if callee_symbol_id:
                incoming_by_callee.setdefault(callee_symbol_id, []).append(edge)

        call_chain_entities = []
        for symbol in symbol_records:
            if symbol.get("chunk_type", symbol.get("entity_type", "")) not in self.callable_types:
                continue

            symbol_id = symbol["symbol_id"]
            outgoing_edges = outgoing_by_caller.get(symbol_id, [])
            incoming_edges = incoming_by_callee.get(symbol_id, [])
            if not outgoing_edges and not incoming_edges:
                continue

            file_entity = file_level_by_path.get(symbol.get("file_path", ""))
            module_entity = module_level_by_key.get(symbol.get("module_key", ""))
            call_chain_facts = self._build_call_chain_facts(
                symbol,
                outgoing_edges,
                incoming_edges,
                explained_entities,
                file_level_by_path,
                module_level_by_key,
                file_entity,
                module_entity,
            )
            explanation = self.llm.generate(
                self.prompt_template.format(
                    context=call_chain_facts,
                    question=(
                        f"Explain the local call-chain role of {self._display_symbol(symbol)} "
                        "using only the provided call-chain facts."
                    ),
                )
            ).strip()

            related_file_paths = self._aggregate_unique(
                [[edge.get("caller_file_path", "")] for edge in incoming_edges]
                + [[edge.get("callee_file_path", "")] for edge in outgoing_edges]
                + [[symbol.get("file_path", "")]]
            )
            related_module_keys = self._aggregate_unique(
                [[edge.get("caller_module_key", "")] for edge in incoming_edges]
                + [[edge.get("callee_module_key", "")] for edge in outgoing_edges]
                + [[symbol.get("module_key", "")]]
            )
            resolved_callee_symbols = self._aggregate_unique(
                [[edge.get("callee_symbol", "")] for edge in outgoing_edges]
            )
            caller_symbols = self._aggregate_unique(
                [[edge.get("caller_symbol", "")] for edge in incoming_edges]
            )

            call_chain_entities.append(
                {
                    "entity_id": f"call_chain::{symbol_id}",
                    "entity_level": "call_chain_level",
                    "path": symbol.get("file_path", ""),
                    "file": symbol.get("file_path", ""),
                    "file_name": Path(symbol.get("file_path", "")).name if symbol.get("file_path", "") else "",
                    "base_name": Path(symbol.get("file_path", "")).stem if symbol.get("file_path", "") else "",
                    "source_type": symbol.get("source_type", ""),
                    "symbol_name": symbol.get("symbol_name", ""),
                    "function_name": symbol.get("symbol_name", ""),
                    "parent_symbol": symbol.get("parent_symbol", ""),
                    "chunk_type": "call_chain_level",
                    "entity_type": "call_chain_level",
                    "language": self._language_for_source_type(symbol.get("source_type", "")),
                    "section_path": symbol.get("module_key", ""),
                    "namespace_path": symbol.get("namespace_path", ""),
                    "chunk_index": 1,
                    "total_chunks": 1,
                    "return_type": f"call_chain:{symbol.get('chunk_type', '')}",
                    "parameters": symbol.get("module_key", ""),
                    "leading_comment": "",
                    "include_paths": file_entity.get("include_paths", []) if file_entity else [],
                    "referenced_files": sorted(Path(file_path).name for file_path in related_file_paths if file_path),
                    "module_scope": symbol.get("module_scope", ""),
                    "module_path": symbol.get("module_path", ""),
                    "module_key": symbol.get("module_key", ""),
                    "caller_symbols": caller_symbols,
                    "callee_symbols": resolved_callee_symbols,
                    "incoming_call_count": len(incoming_edges),
                    "outgoing_call_count": len(outgoing_edges),
                    "related_file_paths": related_file_paths,
                    "related_module_keys": related_module_keys,
                    "generated_explanation": explanation,
                    "generated_explanation_prompt_mode": self.prompt_mode,
                    "generated_explanation_model": getattr(self.llm, "model", "unknown"),
                    "generated_explanation_status": "ok",
                    "generated_explanation_error": "",
                    "explanation_generated_from": "call_chain_neighborhood",
                    "code": call_chain_facts,
                }
            )

        return call_chain_entities

    def save(self, call_chain_entities, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(call_chain_entities, file, indent=2, ensure_ascii=False)
            file.write("\n")

    def _build_call_chain_facts(
        self,
        symbol,
        outgoing_edges,
        incoming_edges,
        explained_entities,
        file_level_by_path,
        module_level_by_key,
        file_entity,
        module_entity,
    ):
        central_explanation = self._short_summary(
            explained_entities.get(symbol["symbol_id"], {}).get("generated_explanation", "")
        )
        file_summary = self._short_summary(
            file_entity.get("generated_explanation", "") if file_entity else ""
        )
        module_summary = self._short_summary(
            module_entity.get("generated_explanation", "") if module_entity else ""
        )

        outgoing_lines = []
        for edge in outgoing_edges:
            callee_display = self._edge_callee_display(edge)
            line = (
                f"- {callee_display} "
                f"[resolution={edge.get('resolution_type', '')}, "
                f"confidence={edge.get('confidence', '')}]"
            )
            callee_file_entity = file_level_by_path.get(edge.get("callee_file_path", ""))
            callee_module_entity = module_level_by_key.get(edge.get("callee_module_key", ""))
            callee_file_summary = self._short_summary(
                callee_file_entity.get("generated_explanation", "") if callee_file_entity else ""
            )
            callee_module_summary = self._short_summary(
                callee_module_entity.get("generated_explanation", "") if callee_module_entity else ""
            )
            if callee_file_summary:
                line += f" | file_summary={callee_file_summary}"
            if callee_module_summary:
                line += f" | module_summary={callee_module_summary}"
            outgoing_lines.append(line)

        incoming_lines = []
        for edge in incoming_edges:
            caller_display = self._edge_caller_display(edge)
            line = (
                f"- {caller_display} "
                f"[resolution={edge.get('resolution_type', '')}, "
                f"confidence={edge.get('confidence', '')}]"
            )
            caller_file_entity = file_level_by_path.get(edge.get("caller_file_path", ""))
            caller_module_entity = module_level_by_key.get(edge.get("caller_module_key", ""))
            caller_file_summary = self._short_summary(
                caller_file_entity.get("generated_explanation", "") if caller_file_entity else ""
            )
            caller_module_summary = self._short_summary(
                caller_module_entity.get("generated_explanation", "") if caller_module_entity else ""
            )
            if caller_file_summary:
                line += f" | file_summary={caller_file_summary}"
            if caller_module_summary:
                line += f" | module_summary={caller_module_summary}"
            incoming_lines.append(line)

        outgoing_text = "\n".join(outgoing_lines) or "- none"
        incoming_text = "\n".join(incoming_lines) or "- none"

        return f"""Central Symbol: {self._display_symbol(symbol)}
Symbol Type: {symbol.get('chunk_type', '')}
File Path: {symbol.get('file_path', '')}
Module Key: {symbol.get('module_key', '')}
Parent Symbol: {symbol.get('parent_symbol', '') or 'none'}
Central Symbol Summary: {central_explanation or 'none'}
Central File Summary: {file_summary or 'none'}
Central Module Summary: {module_summary or 'none'}

Outgoing Calls:
{outgoing_text}

Incoming Calls:
{incoming_text}
"""

    def _display_symbol(self, symbol):
        parent_symbol = symbol.get("parent_symbol", "")
        symbol_name = symbol.get("symbol_name", "")
        if parent_symbol:
            return f"{parent_symbol}::{symbol_name}"
        return symbol_name

    def _edge_callee_display(self, edge):
        callee_symbol = edge.get("callee_symbol", "")
        callee_parent_symbol = edge.get("callee_parent_symbol", "")
        if callee_symbol:
            if callee_parent_symbol:
                return f"{callee_parent_symbol}::{callee_symbol}"
            return callee_symbol
        return edge.get("raw_call", "")

    def _edge_caller_display(self, edge):
        caller_symbol = edge.get("caller_symbol", "")
        caller_parent_symbol = edge.get("caller_parent_symbol", "")
        if caller_parent_symbol:
            return f"{caller_parent_symbol}::{caller_symbol}"
        return caller_symbol

    def _aggregate_unique(self, nested_lists):
        values = []
        seen = set()
        for items in nested_lists:
            for item in items:
                if item and item not in seen:
                    seen.add(item)
                    values.append(item)
        return sorted(values)

    def _short_summary(self, text):
        cleaned = " ".join(text.split())
        if not cleaned:
            return ""
        if len(cleaned) <= self.summary_char_limit:
            return cleaned
        return cleaned[: self.summary_char_limit - 3] + "..."

    def _symbol_id(self, entity):
        file_path = entity.get("path", entity.get("file", ""))
        symbol_name = entity.get("symbol_name", entity.get("function_name", ""))
        parent_symbol = entity.get("parent_symbol", entity.get("class_name", ""))
        entity_type = entity.get("entity_type", entity.get("chunk_type", "entity"))
        return f"{file_path}::{parent_symbol}::{symbol_name}::{entity_type}"

    def _language_for_source_type(self, source_type):
        if source_type in {"cpp", "header"}:
            return "cpp"
        return "text"
