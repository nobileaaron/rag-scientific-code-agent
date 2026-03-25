from pathlib import Path

from src.ingestion.code.reference_extractor import ReferenceExtractor


class HeaderChunker:
    def __init__(self, max_chunk_size):
        self.max_chunk_size = max_chunk_size
        self.reference_extractor = ReferenceExtractor()

    def _split_code(self, code):
        if len(code) <= self.max_chunk_size:
            return [code]

        chunks = []
        start = 0

        while start < len(code):
            end = start + self.max_chunk_size
            split_pos = code.rfind("\n\n", start, end)

            if split_pos == -1 or split_pos <= start:
                split_pos = code.rfind("\n", start, end)

            if split_pos == -1 or split_pos <= start:
                split_pos = end

            chunks.append(code[start:split_pos].strip())
            start = split_pos

            while start < len(code) and code[start] in {"\n", " "}:
                start += 1

        return [chunk for chunk in chunks if chunk]

    def chunk_entities(self, entities):
        chunks = []

        for entity in entities:
            split_chunks = self._split_code(entity["code"])
            file_path = entity["file"]
            file_name = Path(file_path).name
            total_chunks = len(split_chunks)
            references = self.reference_extractor.extract(entity["code"])

            for index, chunk_code in enumerate(split_chunks, start=1):
                chunk_name = entity.get("symbol_name", entity["function_name"])

                chunks.append(
                    {
                        "path": entity.get("path", file_path),
                        "file": entity["file"],
                        "file_name": file_name,
                        "base_name": entity.get("base_name", Path(file_path).stem),
                        "source_type": entity.get("source_type", "header"),
                        "symbol_name": chunk_name,
                        "parent_symbol": entity.get("parent_symbol", entity.get("class_name", "")),
                        "chunk_type": entity.get("chunk_type", entity.get("entity_type", "")),
                        "language": entity.get("language", "cpp"),
                        "section_path": entity.get("section_path", ""),
                        "namespace_path": entity.get("namespace_path", ""),
                        "chunk_index": index,
                        "total_chunks": total_chunks,
                        "function_name": chunk_name,
                        "return_type": entity["return_type"],
                        "parameters": entity["parameters"],
                        "leading_comment": entity.get("leading_comment", ""),
                        "entity_id": entity.get("entity_id", ""),
                        "entity_level": entity.get("entity_level", "function_level"),
                        "explanation_generated_from": entity.get(
                            "explanation_generated_from",
                            "full_entity",
                        ),
                        "generated_explanation": entity.get("generated_explanation", ""),
                        "generated_explanation_prompt_mode": entity.get(
                            "generated_explanation_prompt_mode",
                            "",
                        ),
                        "generated_explanation_model": entity.get(
                            "generated_explanation_model",
                            "",
                        ),
                        "generated_explanation_status": entity.get(
                            "generated_explanation_status",
                            "",
                        ),
                        "generated_explanation_error": entity.get(
                            "generated_explanation_error",
                            "",
                        ),
                        "include_paths": references["include_paths"],
                        "referenced_files": references["referenced_files"],
                        "code": chunk_code,
                        "entity_type": entity.get("entity_type", ""),
                        "class_name": entity.get("class_name", ""),
                    }
                )

        return chunks
