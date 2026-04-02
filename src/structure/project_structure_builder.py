from pathlib import Path
import json
import re

from src.ingestion.code.reference_extractor import ReferenceExtractor
from src.structure.call_graph_builder import TreeSitterCallGraphBuilder


class ProjectStructureBuilder:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.source_root = self.root_path / "src"
        self.reference_extractor = ReferenceExtractor()

    def build(self, source_files, code_entities=None, documentation_files=None):
        code_entities = code_entities or []
        documentation_files = documentation_files or []

        file_records = self._build_file_records(source_files, documentation_files)
        symbol_records = self._build_symbol_records(code_entities)
        file_to_symbols = self._build_file_to_symbols(symbol_records)
        module_to_files = self._build_module_to_files(file_records)
        module_records = self._build_module_records(module_to_files, file_records)

        include_edges = self._build_include_edges(file_records)
        call_edges, call_graph_status = self._build_call_edges(code_entities, symbol_records)
        ownership_edges = self._build_ownership_edges(symbol_records)
        inheritance_edges = self._build_inheritance_edges(symbol_records)
        symbol_to_file = {
            symbol["symbol_id"]: symbol["file_path"]
            for symbol in symbol_records
        }

        for file_record in file_records:
            file_record["symbols"] = file_to_symbols.get(file_record["path"], [])

        structure = {
            "project_root": str(self.root_path),
            "source_root": str(self.source_root),
            "files": file_records,
            "modules": module_records,
            "symbols": symbol_records,
            "relationships": {
                "include_edges": include_edges,
                "call_edges": call_edges,
                "ownership_edges": ownership_edges,
                "inheritance_edges": inheritance_edges,
            },
            "indexes": {
                "file_to_symbols": file_to_symbols,
                "module_to_files": module_to_files,
                "symbol_to_file": symbol_to_file,
                "module_to_submodules": self._build_module_to_submodules(module_records),
            },
            "status": {
                "call_graph": call_graph_status,
            },
            "summary": {
                "file_count": len(file_records),
                "module_count": len(module_records),
                "symbol_count": len(symbol_records),
                "include_edge_count": len(include_edges),
                "call_edge_count": len(call_edges),
                "ownership_edge_count": len(ownership_edges),
                "inheritance_edge_count": len(inheritance_edges),
            },
        }

        return structure

    def save(self, structure, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(structure, file, indent=2, ensure_ascii=False)
            file.write("\n")

    def print_summary(self, structure):
        summary = structure.get("summary", {})
        print("\nProject structure summary:")
        print(f"Files: {summary.get('file_count', 0)}")
        print(f"Modules: {summary.get('module_count', 0)}")
        print(f"Symbols: {summary.get('symbol_count', 0)}")
        print(f"Include edges: {summary.get('include_edge_count', 0)}")
        print(f"Call edges: {summary.get('call_edge_count', 0)}")
        print(f"Ownership edges: {summary.get('ownership_edge_count', 0)}")
        print(f"Inheritance edges: {summary.get('inheritance_edge_count', 0)}\n")

    def _build_file_records(self, source_files, documentation_files):
        file_records = []

        for file_data in source_files + documentation_files:
            file_path = file_data["path"]
            references = self.reference_extractor.extract(file_data["content"])
            module_scope, module_path = self._module_location_for_file(file_path)
            module_key = self._module_key(module_scope, module_path)

            file_records.append(
                {
                    "path": file_path,
                    "file_name": Path(file_path).name,
                    "base_name": Path(file_path).stem,
                    "source_type": file_data.get("type", self._source_type_from_path(file_path)),
                    "module_scope": module_scope,
                    "module_path": module_path,
                    "module_key": module_key,
                    "parent_module": self._parent_module_key(module_scope, module_path),
                    "include_paths": references["include_paths"],
                    "referenced_files": references["referenced_files"],
                }
            )

        return file_records

    def _build_symbol_records(self, code_entities):
        symbol_records = []

        for entity in code_entities:
            symbol_name = entity.get("symbol_name", entity.get("function_name", ""))
            if not symbol_name:
                continue

            file_path = entity.get("path", entity.get("file", ""))
            module_scope, module_path = self._module_location_for_file(file_path)
            symbol_id = self._symbol_id(entity)

            symbol_records.append(
                {
                    "symbol_id": symbol_id,
                    "symbol_name": symbol_name,
                    "parent_symbol": entity.get("parent_symbol", entity.get("class_name", "")),
                    "entity_type": entity.get("entity_type", entity.get("chunk_type", "")),
                    "chunk_type": entity.get("chunk_type", entity.get("entity_type", "")),
                    "source_type": entity.get("source_type", self._source_type_from_path(file_path)),
                    "file_path": file_path,
                    "file_name": Path(file_path).name if file_path else "",
                    "module_scope": module_scope,
                    "module_path": module_path,
                    "module_key": self._module_key(module_scope, module_path),
                    "return_type": entity.get("return_type", ""),
                    "parameters": entity.get("parameters", ""),
                    "namespace_path": entity.get("namespace_path", ""),
                    "section_path": entity.get("section_path", ""),
                }
            )

        return symbol_records

    def _build_file_to_symbols(self, symbol_records):
        file_to_symbols = {}
        for symbol in symbol_records:
            file_to_symbols.setdefault(symbol["file_path"], []).append(symbol["symbol_id"])
        return file_to_symbols

    def _build_module_to_files(self, file_records):
        module_to_files = {}
        for file_record in file_records:
            module_to_files.setdefault(file_record["module_key"], []).append(file_record["path"])
        return module_to_files

    def _build_module_records(self, module_to_files, file_records):
        module_records = []
        file_lookup = {file_record["path"]: file_record for file_record in file_records}

        all_modules = set(module_to_files)
        for module_key in list(all_modules):
            current = module_key
            while current and not current.endswith(":root"):
                scope, path = self._split_module_key(current)
                parent = self._parent_module_key(scope, path)
                if parent and parent not in all_modules:
                    all_modules.add(parent)
                current = parent

        for module_key in sorted(all_modules):
            module_scope, module_path = self._split_module_key(module_key)
            file_paths = sorted(module_to_files.get(module_key, []))
            source_types = sorted(
                {
                    file_lookup[file_path]["source_type"]
                    for file_path in file_paths
                    if file_path in file_lookup
                }
            )
            module_records.append(
                {
                    "module_key": module_key,
                    "module_scope": module_scope,
                    "module_path": module_path,
                    "module_name": Path(module_path).name if module_path != "root" else "root",
                    "parent_module": self._parent_module_key(module_scope, module_path),
                    "file_paths": file_paths,
                    "file_count": len(file_paths),
                    "source_types": source_types,
                }
            )

        return module_records

    def _build_include_edges(self, file_records):
        include_edges = []

        for file_record in file_records:
            for include_path in file_record.get("include_paths", []):
                include_edges.append(
                    {
                        "source_file": file_record["path"],
                        "source_module_key": file_record["module_key"],
                        "source_module_scope": file_record["module_scope"],
                        "source_module": file_record["module_path"],
                        "target_include_path": include_path,
                        "target_file_name": Path(include_path).name,
                        "relationship": "includes",
                    }
                )

        return include_edges

    def _build_ownership_edges(self, symbol_records):
        ownership_edges = []
        seen_edges = set()

        for symbol in symbol_records:
            parent_symbol = symbol.get("parent_symbol", "")
            if not parent_symbol:
                continue

            owned_symbol = symbol["symbol_name"]
            if parent_symbol == owned_symbol:
                continue

            edge_key = (
                symbol["file_path"],
                parent_symbol,
                owned_symbol,
            )
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            ownership_edges.append(
                {
                    "owner_symbol": parent_symbol,
                    "owned_symbol": owned_symbol,
                    "owned_symbol_id": symbol["symbol_id"],
                    "file_path": symbol["file_path"],
                    "relationship": "owns_symbol",
                }
            )

        return ownership_edges

    def _build_call_edges(self, code_entities, symbol_records):
        try:
            call_graph_builder = TreeSitterCallGraphBuilder(symbol_records)
        except Exception as exc:
            return [], {
                "backend": "tree_sitter",
                "available": False,
                "reason": str(exc),
            }

        call_edges = call_graph_builder.build(code_entities)
        return call_edges, {
            "backend": "tree_sitter",
            "available": True,
            "reason": "",
        }

    def _build_inheritance_edges(self, symbol_records):
        inheritance_edges = []

        for symbol in symbol_records:
            if symbol.get("chunk_type") not in {"class", "struct"}:
                continue

            for base_class in self._extract_base_classes(symbol.get("parameters", "")):
                inheritance_edges.append(
                    {
                        "derived_symbol": symbol["symbol_name"],
                        "derived_symbol_id": symbol["symbol_id"],
                        "base_symbol": base_class,
                        "file_path": symbol["file_path"],
                        "relationship": "inherits",
                    }
                )

        return inheritance_edges

    def _build_module_to_submodules(self, module_records):
        module_to_submodules = {}
        for module_record in module_records:
            parent_module = module_record.get("parent_module")
            if not parent_module:
                continue
            module_to_submodules.setdefault(parent_module, []).append(module_record["module_key"])

        for parent_module, submodules in module_to_submodules.items():
            module_to_submodules[parent_module] = sorted(set(submodules))

        return module_to_submodules

    def _module_location_for_file(self, file_path):
        path_obj = Path(file_path)
        try:
            relative_parent = path_obj.relative_to(self.source_root).parent
            relative_parent_text = relative_parent.as_posix()
            return "source", "root" if relative_parent_text in {"", "."} else relative_parent_text
        except ValueError:
            try:
                relative_parent = path_obj.relative_to(self.root_path).parent
            except ValueError:
                relative_parent = path_obj.parent

        relative_parent_text = relative_parent.as_posix()
        scope = self._infer_non_source_scope(file_path)
        return scope, "root" if relative_parent_text in {"", "."} else relative_parent_text

    def _parent_module_key(self, module_scope, module_path):
        if not module_path or module_path == "root":
            return ""

        parent = Path(module_path).parent.as_posix()
        parent_path = "root" if parent in {"", "."} else parent
        return self._module_key(module_scope, parent_path)

    def _module_key(self, module_scope, module_path):
        return f"{module_scope}:{module_path}"

    def _split_module_key(self, module_key):
        if ":" not in module_key:
            return "source", module_key
        return tuple(module_key.split(":", 1))

    def _source_type_from_path(self, file_path):
        suffix = Path(file_path).suffix.lower()
        if suffix == ".cpp":
            return "cpp"
        if suffix in {".h", ".hpp"}:
            return "header"
        return "documentation"

    def _symbol_id(self, entity):
        file_path = entity.get("path", entity.get("file", ""))
        symbol_name = entity.get("symbol_name", entity.get("function_name", ""))
        parent_symbol = entity.get("parent_symbol", entity.get("class_name", ""))
        entity_type = entity.get("entity_type", entity.get("chunk_type", "entity"))
        return f"{file_path}::{parent_symbol}::{symbol_name}::{entity_type}"

    def _extract_base_classes(self, inheritance_text):
        if not inheritance_text:
            return []

        cleaned_text = inheritance_text
        if cleaned_text.startswith(":"):
            cleaned_text = cleaned_text[1:]

        base_classes = []
        for base_part in cleaned_text.split(","):
            normalized = re.sub(
                r"\b(public|private|protected|virtual)\b",
                "",
                base_part,
            ).strip()
            if normalized:
                base_classes.append(normalized)

        return base_classes

    def _infer_non_source_scope(self, file_path):
        path_obj = Path(file_path)
        try:
            relative_parts = path_obj.relative_to(self.root_path).parts
        except ValueError:
            return "repo"

        if not relative_parts:
            return "repo"

        first_part = relative_parts[0]
        if first_part in {"test", "unit_tests", "ci", "examples", "doc", "alpine"}:
            return first_part
        return "repo"
