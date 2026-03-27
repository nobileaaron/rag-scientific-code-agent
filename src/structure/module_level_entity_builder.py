import json
from pathlib import Path

from src.prompts.prompt_templates import get_prompt_template


class ModuleLevelEntityBuilder:
    def __init__(self, llm, prompt_mode="module_level", file_summary_char_limit=220):
        self.llm = llm
        self.prompt_mode = prompt_mode
        self.prompt_template = get_prompt_template(prompt_mode)
        self.file_summary_char_limit = file_summary_char_limit

    def build(self, project_structure, file_level_entities):
        file_level_by_path = {
            entity["path"]: entity
            for entity in file_level_entities
        }
        file_records_by_path = {
            file_record["path"]: file_record
            for file_record in project_structure.get("files", [])
        }
        indexes = project_structure.get("indexes", {})
        module_to_files = indexes.get("module_to_files", {})
        module_to_submodules = indexes.get("module_to_submodules", {})
        module_entities = []
        candidate_module_records = [
            module_record
            for module_record in project_structure.get("modules", [])
            if module_record.get("module_path") != "root"
        ]
        explained_count = 0
        total_modules = 0

        for module_record in candidate_module_records:
            module_key = module_record["module_key"]
            descendant_module_keys = self._descendant_modules(module_key, module_to_submodules)
            descendant_file_paths = sorted(
                {
                    file_path
                    for descendant_module_key in descendant_module_keys
                    for file_path in module_to_files.get(descendant_module_key, [])
                }
            )
            if descendant_file_paths:
                total_modules += 1

        for module_record in candidate_module_records:
            module_key = module_record["module_key"]
            descendant_module_keys = self._descendant_modules(module_key, module_to_submodules)
            descendant_file_paths = sorted(
                {
                    file_path
                    for descendant_module_key in descendant_module_keys
                    for file_path in module_to_files.get(descendant_module_key, [])
                }
            )
            if not descendant_file_paths:
                continue

            file_records = [
                file_records_by_path[file_path]
                for file_path in descendant_file_paths
                if file_path in file_records_by_path
            ]
            member_file_entities = [
                file_level_by_path[file_path]
                for file_path in descendant_file_paths
                if file_path in file_level_by_path
            ]
            module_facts = self._build_module_facts(
                module_record,
                descendant_module_keys,
                file_records,
                member_file_entities,
            )
            explanation = self.llm.generate(
                self.prompt_template.format(
                    context=module_facts,
                    question=(
                        f"Explain the role of module {module_record['module_key']} using only "
                        "the provided module facts and file-level summaries."
                    ),
                )
            ).strip()

            module_entities.append(
                {
                    "entity_id": f"module_level::{module_key}",
                    "entity_level": "module_level",
                    "path": module_record["module_key"],
                    "file": module_record["module_key"],
                    "file_name": module_record["module_name"],
                    "base_name": module_record["module_name"],
                    "source_type": "module",
                    "symbol_name": module_record["module_name"],
                    "function_name": module_record["module_name"],
                    "parent_symbol": module_record.get("parent_module", ""),
                    "chunk_type": "module_level",
                    "entity_type": "module_level",
                    "language": "text",
                    "section_path": module_record["module_key"],
                    "namespace_path": "",
                    "chunk_index": 1,
                    "total_chunks": 1,
                    "return_type": f"module:{module_record['module_scope']}",
                    "parameters": module_record.get("parent_module", ""),
                    "leading_comment": "",
                    "include_paths": self._aggregate_unique(
                        file_record.get("include_paths", [])
                        for file_record in file_records
                    ),
                    "referenced_files": self._aggregate_unique(
                        file_record.get("referenced_files", [])
                        for file_record in file_records
                    ),
                    "module_scope": module_record["module_scope"],
                    "module_path": module_record["module_path"],
                    "module_key": module_key,
                    "module_name": module_record["module_name"],
                    "parent_module": module_record.get("parent_module", ""),
                    "descendant_module_keys": descendant_module_keys,
                    "contained_file_paths": descendant_file_paths,
                    "contained_file_names": [Path(file_path).name for file_path in descendant_file_paths],
                    "contained_symbol_names": self._aggregate_unique(
                        entity.get("contained_symbol_names", [])
                        for entity in member_file_entities
                    ),
                    "contained_symbol_types": self._aggregate_unique(
                        entity.get("contained_symbol_types", [])
                        for entity in member_file_entities
                    ),
                    "file_level_modes": self._aggregate_unique(
                        [[entity.get("file_level_mode", "")]]
                        for entity in member_file_entities
                    ),
                    "generated_explanation": explanation,
                    "generated_explanation_prompt_mode": self.prompt_mode,
                    "generated_explanation_model": getattr(self.llm, "model", "unknown"),
                    "generated_explanation_status": "ok",
                    "generated_explanation_error": "",
                    "explanation_generated_from": "aggregated_module_facts",
                    "code": module_facts,
                }
            )
            explained_count += 1
            print(f"  explained {explained_count}/{total_modules} module_level entities")

        return module_entities

    def save(self, module_entities, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(module_entities, file, indent=2, ensure_ascii=False)
            file.write("\n")

    def _build_module_facts(
        self,
        module_record,
        descendant_module_keys,
        file_records,
        member_file_entities,
    ):
        file_lines = []
        for entity in member_file_entities:
            summary = self._short_summary(entity.get("generated_explanation", ""))
            file_line = (
                f"- {entity.get('file_name', '')} "
                f"[mode={entity.get('file_level_mode', 'unknown')}, "
                f"source_type={entity.get('source_type', '')}]"
            )
            if summary:
                file_line += f" | summary={summary}"
            file_lines.append(file_line)

        file_text = "\n".join(file_lines) or "- none"
        include_text = "\n".join(
            f"- {include_path}"
            for include_path in self._aggregate_unique(
                file_record.get("include_paths", [])
                for file_record in file_records
            )
        ) or "- none"
        referenced_text = "\n".join(
            f"- {file_name}"
            for file_name in self._aggregate_unique(
                file_record.get("referenced_files", [])
                for file_record in file_records
            )
        ) or "- none"
        symbol_text = "\n".join(
            f"- {symbol_name}"
            for symbol_name in self._aggregate_unique(
                entity.get("contained_symbol_names", [])
                for entity in member_file_entities
            )
        ) or "- none"
        source_types = sorted(
            {
                file_record.get("source_type", "")
                for file_record in file_records
                if file_record.get("source_type", "")
            }
        )
        submodule_text = "\n".join(
            f"- {submodule_key}"
            for submodule_key in descendant_module_keys
            if submodule_key != module_record["module_key"]
        ) or "- none"

        return f"""Module Key: {module_record['module_key']}
Module Name: {module_record['module_name']}
Module Scope: {module_record['module_scope']}
Module Path: {module_record['module_path']}
Parent Module: {module_record.get('parent_module', '') or 'none'}
Direct File Count: {module_record.get('file_count', 0)}
Descendant File Count: {len(file_records)}
Source Types: {', '.join(source_types) or 'none'}

Descendant Modules:
{submodule_text}

Member Files:
{file_text}

Aggregated Symbol Names:
{symbol_text}

Aggregated Include Paths:
{include_text}

Aggregated Referenced Files:
{referenced_text}
"""

    def _descendant_modules(self, module_key, module_to_submodules):
        descendants = []
        stack = [module_key]
        seen = set()

        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            descendants.append(current)
            stack.extend(module_to_submodules.get(current, []))

        return sorted(descendants)

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
        if len(cleaned) <= self.file_summary_char_limit:
            return cleaned
        return cleaned[: self.file_summary_char_limit - 3] + "..."
