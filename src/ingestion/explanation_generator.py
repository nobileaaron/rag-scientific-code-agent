from pathlib import Path

from src.ingestion.code.reference_extractor import ReferenceExtractor
from src.prompts.prompt_templates import get_prompt_template


class EntityExplanationGenerator:
    def __init__(
        self,
        llm,
        prompt_mode="general",
        allowed_chunk_types=None,
        min_content_length=120,
        pilot_limit=None,
    ):
        self.llm = llm
        self.prompt_mode = prompt_mode
        self.prompt_template = get_prompt_template(prompt_mode)
        self.allowed_chunk_types = set(
            allowed_chunk_types
            or {
                "function_definition",
                "method_definition",
                "class",
                "struct",
                "section",
                "paragraph",
                "code_block",
            }
        )
        self.min_content_length = min_content_length
        self.pilot_limit = pilot_limit
        self.generated_count = 0
        self.entity_counter = 0
        self.reference_extractor = ReferenceExtractor()
        self.stats = {
            "seen": 0,
            "eligible": 0,
            "explained": 0,
            "loaded_from_snapshot": 0,
            "skipped_by_type": 0,
            "skipped_low_information": 0,
            "skipped_by_pilot": 0,
            "errors": 0,
        }

    def enrich_entities(self, entities, entity_level):
        if not entities:
            return entities

        batch_target = self._count_batch_target(entities)
        batch_explained = 0
        print(
            f"annotating {len(entities)} {entity_level} entities for explanation generation..."
        )
        if self.pilot_limit is not None:
            remaining = max(self.pilot_limit - self.generated_count, 0)
            print(
                f"  pilot mode enabled: up to {remaining} additional entities "
                f"will receive explanations in this run."
            )

        for entity in entities:
            self.stats["seen"] += 1
            self._assign_entity_metadata(entity, entity_level)

            skip_reason = self._skip_reason(entity)
            if skip_reason == "skipped_by_type":
                self.stats["skipped_by_type"] += 1
                self._mark_skipped(entity, "skipped_by_type")
                continue
            if skip_reason == "skipped_low_information":
                self.stats["skipped_low_information"] += 1
                self._mark_skipped(entity, "skipped_low_information")
                continue

            self.stats["eligible"] += 1
            if self._has_existing_explanation(entity):
                self.stats["loaded_from_snapshot"] += 1
                continue
            if self.pilot_limit is not None and self.generated_count >= self.pilot_limit:
                self.stats["skipped_by_pilot"] += 1
                self._mark_skipped(entity, "skipped_by_pilot")
                continue

            self._generate_explanation(entity)
            if entity.get("generated_explanation_status") == "ok":
                batch_explained += 1
                print(f"  explained {batch_explained}/{batch_target} {entity_level} entities")

        return entities

    def print_summary(self):
        print("\nExplanation generation summary:")
        print(f"Seen entities: {self.stats['seen']}")
        print(f"Eligible entities: {self.stats['eligible']}")
        print(f"Explained entities: {self.stats['explained']}")
        print(f"Loaded from snapshot: {self.stats['loaded_from_snapshot']}")
        print(f"Skipped by type: {self.stats['skipped_by_type']}")
        print(f"Skipped low-information entities: {self.stats['skipped_low_information']}")
        print(f"Skipped by pilot limit: {self.stats['skipped_by_pilot']}")
        print(f"Explanation errors: {self.stats['errors']}\n")

    def _assign_entity_metadata(self, entity, entity_level):
        self.entity_counter += 1
        entity.setdefault("entity_id", self._build_entity_id(entity, entity_level))
        entity["entity_level"] = entity_level
        entity.setdefault("explanation_generated_from", "full_entity")
        entity.setdefault("generated_explanation", "")
        entity.setdefault("generated_explanation_error", "")
        entity.setdefault("generated_explanation_prompt_mode", self.prompt_mode)
        entity.setdefault("generated_explanation_model", getattr(self.llm, "model", "unknown"))

    def _build_entity_id(self, entity, entity_level):
        symbol = entity.get("symbol_name", entity.get("function_name", "anonymous"))
        parent_symbol = entity.get("parent_symbol", entity.get("class_name", ""))
        chunk_type = entity.get("chunk_type", entity.get("entity_type", "entity"))
        file_name = entity.get("file_name", Path(entity.get("file", "")).name)
        return (
            f"{entity_level}:{file_name}:{chunk_type}:{parent_symbol}:{symbol}:"
            f"{self.entity_counter}"
        )

    def _skip_reason(self, entity):
        chunk_type = entity.get("chunk_type", entity.get("entity_type", ""))
        if chunk_type not in self.allowed_chunk_types:
            return "skipped_by_type"
        if self._is_low_information(entity.get("code", "")):
            return "skipped_low_information"
        return None

    def _is_low_information(self, content):
        stripped = content.strip()
        if not stripped:
            return True
        if stripped in {"{", "}", "};"}:
            return True
        if len(stripped) < self.min_content_length:
            return True

        alnum_chars = sum(char.isalnum() for char in stripped)
        return alnum_chars < max(25, self.min_content_length // 3)

    def _count_batch_target(self, entities):
        eligible_count = sum(
            1
            for entity in entities
            if self._skip_reason(entity) is None and not self._has_existing_explanation(entity)
        )
        if self.pilot_limit is None:
            return eligible_count
        remaining = max(self.pilot_limit - self.generated_count, 0)
        return min(eligible_count, remaining)

    def _mark_skipped(self, entity, status):
        entity["generated_explanation_status"] = status
        entity["generated_explanation"] = ""
        entity["generated_explanation_error"] = ""

    def _has_existing_explanation(self, entity):
        return (
            entity.get("generated_explanation_status") == "ok"
            and bool(entity.get("generated_explanation", "").strip())
        )

    def _generate_explanation(self, entity):
        try:
            prompt = self.prompt_template.format(
                context=self._build_entity_context(entity),
                question=(
                    "Explain this full entity as part of the IPPL scientific C++ codebase. "
                    "This explanation will later be attached to any smaller retrieval chunks "
                    "produced from this entity."
                ),
            )
            entity["generated_explanation"] = self.llm.generate(prompt).strip()
            entity["generated_explanation_status"] = "ok"
            entity["generated_explanation_error"] = ""
            self.generated_count += 1
            self.stats["explained"] += 1
        except Exception as exc:  # pragma: no cover - defensive runtime safeguard
            entity["generated_explanation"] = ""
            entity["generated_explanation_status"] = "error"
            entity["generated_explanation_error"] = str(exc)
            self.stats["errors"] += 1

    def _build_entity_context(self, entity):
        symbol_name = entity.get("symbol_name", entity.get("function_name", ""))
        parent_symbol = entity.get("parent_symbol", entity.get("class_name", ""))
        chunk_type = entity.get("chunk_type", entity.get("entity_type", ""))
        source_type = entity.get("source_type", "")
        file_path = entity.get("path", entity.get("file", ""))
        language = entity.get("language", "")
        section_path = entity.get("section_path", entity.get("parameters", ""))
        return_type = entity.get("return_type", "")
        leading_comment = entity.get("leading_comment", "")
        references = self.reference_extractor.extract(entity.get("code", ""))
        include_paths = ", ".join(references["include_paths"]) or "No linked includes found."
        referenced_files = (
            ", ".join(references["referenced_files"]) or "No referenced files found."
        )

        return f"""
Entity Level: {entity.get("entity_level", "")}
Explanation Source: full entity before splitting into retrieval chunks
Source Type: {source_type}
Chunk Type: {chunk_type}
Symbol: {symbol_name}
Parent Symbol: {parent_symbol}
Path: {file_path}
Language: {language}
Return Type: {return_type}
Parameters / Section Path: {section_path}
Leading Comment:
{leading_comment or "No comment found."}
Include Paths:
{include_paths}
Referenced Files:
{referenced_files}
Content:
{entity["code"]}
"""
