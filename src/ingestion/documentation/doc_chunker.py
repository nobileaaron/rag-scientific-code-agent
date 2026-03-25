from pathlib import Path


class DocChunker:
    def __init__(self, max_chunk_size):
        self.max_chunk_size = max_chunk_size

    def _language_from_file_type(self, file_type):
        language_map = {
            "md": "markdown",
            "rst": "rst",
            "txt": "text",
        }
        return language_map.get(file_type, file_type or "text")

    def _split_content(self, content):
        if len(content) <= self.max_chunk_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + self.max_chunk_size
            split_pos = content.rfind("\n\n", start, end)

            if split_pos == -1 or split_pos <= start:
                split_pos = content.rfind("\n", start, end)

            if split_pos == -1 or split_pos <= start:
                split_pos = end

            chunks.append(content[start:split_pos].strip())
            start = split_pos

            while start < len(content) and content[start] in {"\n", " "}:
                start += 1

        return [chunk for chunk in chunks if chunk]

    def chunk_sections(self, sections):
        chunks = []

        for section in sections:
            split_chunks = self._split_content(section["content"])
            file_path = section["path"]
            file_name = section.get("file_name") or Path(file_path).name
            total_chunks = len(split_chunks)

            for index, chunk_content in enumerate(split_chunks, start=1):
                symbol_name = section["section_title"]
                if total_chunks > 1:
                    symbol_name = f"{symbol_name}_{index}"

                chunks.append(
                    {
                        "path": file_path,
                        "file": section["path"],
                        "source_type": "documentation",
                        "symbol_name": symbol_name,
                        "parent_symbol": section["doc_type"],
                        "chunk_type": section["section_type"],
                        "language": self._language_from_file_type(section["file_type"]),
                        "section_path": section["section_path"],
                        "namespace_path": "",
                        "chunk_index": index,
                        "total_chunks": total_chunks,
                        "function_name": symbol_name,
                        "return_type": f"doc:{section['file_type']}",
                        "parameters": section["section_path"],
                        "entity_id": section.get("entity_id", ""),
                        "entity_level": section.get("entity_level", "documentation_section_level"),
                        "explanation_generated_from": section.get(
                            "explanation_generated_from",
                            "full_entity",
                        ),
                        "generated_explanation": section.get("generated_explanation", ""),
                        "generated_explanation_prompt_mode": section.get(
                            "generated_explanation_prompt_mode",
                            "",
                        ),
                        "generated_explanation_model": section.get(
                            "generated_explanation_model",
                            "",
                        ),
                        "generated_explanation_status": section.get(
                            "generated_explanation_status",
                            "",
                        ),
                        "generated_explanation_error": section.get(
                            "generated_explanation_error",
                            "",
                        ),
                        "code": chunk_content,
                        "entity_type": section["section_type"],
                        "class_name": section["doc_type"],
                        "file_name": file_name,
                        "section_title": section["section_title"],
                        "section_index": section["section_index"],
                    }
                )

        return chunks
