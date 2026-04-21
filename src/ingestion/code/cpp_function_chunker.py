from pathlib import Path

from src.ingestion.code.reference_extractor import ReferenceExtractor


class CppFunctionChunker:
    def __init__(self, max_chunk_size):
        self.max_chunk_size = max_chunk_size
        self.reference_extractor = ReferenceExtractor()

    def _split_function(self, function_code):
        if len(function_code) <= self.max_chunk_size:
            return [function_code]

        chunks = []
        start = 0

        while start < len(function_code):
            end = start + self.max_chunk_size
            newline_pos = function_code.rfind("\n", start, end)

            if newline_pos != -1 and newline_pos > start:
                end = newline_pos

            chunks.append(function_code[start:end])
            start = end

        return chunks

    def _prepend_leading_comment(self, function):
        comment = (function.get("leading_comment") or "").strip()
        code = function.get("code") or ""
        if not comment:
            return code
        if code.lstrip().startswith(comment.strip()):
            return code
        return comment + "\n\n" + code

    def chunk_functions(self, functions):
        chunks = []

        for function in functions:
            split_chunks = self._split_function(self._prepend_leading_comment(function))
            file_path = function["file"]
            file_name = Path(file_path).name
            total_chunks = len(split_chunks)
            references = self.reference_extractor.extract(function["code"])

            for i, chunk_code in enumerate(split_chunks, start=1):
                chunk_name = function.get("symbol_name", function["function_name"])

                chunks.append(
                    {
                        "path": function.get("path", file_path),
                        "file": function["file"],
                        "file_name": file_name,
                        "base_name": function.get("base_name", Path(file_path).stem),
                        "source_type": function.get("source_type", "cpp"),
                        "symbol_name": chunk_name,
                        "parent_symbol": function.get("parent_symbol", ""),
                        "chunk_type": function.get("chunk_type", "function_definition"),
                        "language": function.get("language", "cpp"),
                        "section_path": function.get("section_path", function.get("namespace_path", "")),
                        "namespace_path": function.get("namespace_path", ""),
                        "chunk_index": i,
                        "total_chunks": total_chunks,
                        "function_name": chunk_name,
                        "return_type": function["return_type"],
                        "parameters": function["parameters"],
                        "leading_comment": function.get("leading_comment", ""),
                        "entity_id": function.get("entity_id", ""),
                        "entity_level": function.get("entity_level", "function_level"),
                        "explanation_generated_from": function.get(
                            "explanation_generated_from",
                            "full_entity",
                        ),
                        "generated_explanation": function.get("generated_explanation", ""),
                        "generated_explanation_prompt_mode": function.get(
                            "generated_explanation_prompt_mode",
                            "",
                        ),
                        "generated_explanation_model": function.get(
                            "generated_explanation_model",
                            "",
                        ),
                        "generated_explanation_status": function.get(
                            "generated_explanation_status",
                            "",
                        ),
                        "generated_explanation_error": function.get(
                            "generated_explanation_error",
                            "",
                        ),
                        "include_paths": references["include_paths"],
                        "referenced_files": references["referenced_files"],
                        "code": chunk_code,
                        "entity_type": function.get("entity_type", "function_definition"),
                        "class_name": function.get("class_name", ""),
                    }
                )

        return chunks
