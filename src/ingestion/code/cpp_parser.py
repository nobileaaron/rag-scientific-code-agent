from pathlib import Path
import re

from src.ingestion.code.comment_extractor import CommentExtractor


def attach_top_of_file_comment_to_first_function(file_functions, file_leading_comment):
    if not file_functions or not file_leading_comment:
        return

    primary = None
    for function in file_functions:
        if function.get("symbol_name") == function.get("base_name"):
            primary = function
            break
    if primary is None:
        for function in file_functions:
            if function.get("class_name") == function.get("base_name"):
                primary = function
                break
    if primary is None:
        primary = file_functions[0]

    existing = primary.get("leading_comment", "")
    if existing and file_leading_comment in existing:
        return
    if existing:
        primary["leading_comment"] = file_leading_comment + "\n\n" + existing
    else:
        primary["leading_comment"] = file_leading_comment


class TreeSitterParser:
    def __init__(self):
        try:
            from tree_sitter_languages import get_language
            from tree_sitter import Parser
        except ImportError as exc:
            raise ImportError(
                "Tree-sitter parser requested, but 'tree_sitter' and "
                "'tree_sitter_languages' are not installed."
            ) from exc

        #import parser from tree_sitter and configure to cpp grammar
        self._parser = Parser()
        language = get_language("cpp")
        if hasattr(self._parser, "set_language"):
            self._parser.set_language(language)
        else:
            self._parser.language = language
        self.comment_extractor = CommentExtractor()

    #Take raw file text + tree-sitter node and return exact substring fo the file
    #corresponding to that node, this function converts a node into actual source text
    def _node_text(self, content, node):
        return content[node.start_byte : node.end_byte]
    
    #looks through the direct children of a node
    #returns first child whose type matches one of the requested node types
    #TS trees are nested -> need helper functions to locate important child nodes
    def _find_child(self, node, node_types):
        for child in node.children:
            if child.type in node_types:
                return child
        return None

    def _find_first_descendant(self, node, node_types):
        for child in self._walk(node):
            if child.type in node_types:
                return child
        return None

    #recusively traverse the syntax tree
    #want to inspect the whole parsed file -> need a way to visit everything
    def _walk(self, node):
        yield node
        for child in node.children:
            yield from self._walk(child)

    def _split_qualified_name(self, raw_name):
        name_parts = [part.strip() for part in raw_name.split("::") if part.strip()]
        if not name_parts:
            return "", "", ""

        symbol_name = name_parts[-1]
        parent_symbol = "::".join(name_parts[:-1])
        class_name = name_parts[-2] if len(name_parts) > 1 else ""

        return symbol_name, parent_symbol, class_name

    def _namespace_path_for_node(self, content, node):
        namespaces = []
        current = getattr(node, "parent", None)
        while current is not None:
            if current.type == "namespace_definition":
                namespace_name = self._namespace_name(content, current)
                if namespace_name:
                    namespaces.append(namespace_name)
            current = getattr(current, "parent", None)
        return "::".join(reversed(namespaces))

    def _namespace_name(self, content, node):
        body = self._find_child(node, {"declaration_list"})
        header_end = body.start_byte if body is not None else node.end_byte
        namespace_header = content[node.start_byte:header_end]
        match = re.search(
            r"\bnamespace\s+(?:inline\s+)?([A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*)",
            namespace_header,
        )
        if not match:
            return ""
        return match.group(1)

    def _namespace_from_qualified_name(self, raw_name):
        name_parts = [part.strip() for part in raw_name.split("::") if part.strip()]
        if len(name_parts) <= 2:
            return ""
        return "::".join(name_parts[:-2])

    def _build_qualified_symbol_name(
        self,
        raw_name,
        namespace_path,
        parent_symbol,
        symbol_name,
    ):
        raw_name = str(raw_name or "").strip()
        namespace_path = str(namespace_path or "").strip()
        parent_symbol = str(parent_symbol or "").strip()
        symbol_name = str(symbol_name or "").strip()

        if "::" in raw_name:
            if namespace_path and not raw_name.startswith(f"{namespace_path}::"):
                return f"{namespace_path}::{raw_name}"
            return raw_name

        name_parts = []
        if namespace_path:
            name_parts.extend(part for part in namespace_path.split("::") if part)
        if parent_symbol and parent_symbol != symbol_name:
            name_parts.extend(part for part in parent_symbol.split("::") if part)
        if symbol_name:
            name_parts.append(symbol_name)
        return "::".join(name_parts)

    def _append_unique_entity(self, entities, seen_entities, entity):
        entity_key = (
            entity["file"],
            entity["entity_type"],
            entity["function_name"],
            entity["code"],
        )
        if entity_key in seen_entities:
            return
        seen_entities.add(entity_key)
        entities.append(entity)

    def _is_global_scope_node(self, node):
        blocked_ancestors = {
            "function_definition",
            "compound_statement",
            "class_specifier",
            "struct_specifier",
            "field_declaration_list",
        }
        current = getattr(node, "parent", None)
        while current is not None:
            if current.type in blocked_ancestors:
                return False
            current = getattr(current, "parent", None)
        return True

    def _namespace_entity_name(self, content, node):
        namespace_name = self._namespace_name(content, node)
        if namespace_name:
            return namespace_name
        return "anonymous_namespace"

    def _class_parent_for_node(self, content, node):
        current = getattr(node, "parent", None)
        while current is not None:
            if current.type in {"class_specifier", "struct_specifier"}:
                name_node = self._find_first_descendant(
                    current,
                    {"type_identifier", "identifier"},
                )
                if name_node is not None:
                    return self._node_text(content, name_node).strip()
            current = getattr(current, "parent", None)
        return ""

    def _build_lightweight_entity_record(
        self,
        content,
        path,
        node,
        entity_type,
        symbol_name,
        return_type="",
        parameters="",
        parent_symbol="",
        namespace_path=None,
        code=None,
    ):
        file_path = Path(path)
        symbol_name = str(symbol_name or "").strip()
        parent_symbol = str(parent_symbol or "").strip()
        namespace_path = (
            self._namespace_path_for_node(content, node)
            if namespace_path is None
            else str(namespace_path or "").strip()
        )
        qualified_symbol_name = self._build_qualified_symbol_name(
            "",
            namespace_path,
            parent_symbol,
            symbol_name,
        )

        return {
            "path": path,
            "file": path,
            "file_name": file_path.name,
            "base_name": file_path.stem,
            "language": "cpp",
            "source_type": "cpp",
            "entity_type": entity_type,
            "chunk_type": entity_type,
            "symbol_name": symbol_name,
            "function_name": symbol_name,
            "parent_symbol": parent_symbol,
            "class_name": parent_symbol,
            "return_type": return_type or entity_type,
            "parameters": parameters,
            "section_path": parent_symbol,
            "namespace_path": namespace_path,
            "qualified_symbol_name": qualified_symbol_name,
            "chunk_index": 1,
            "total_chunks": 1,
            "leading_comment": self.comment_extractor.extract_leading_comment(
                content,
                node.start_byte,
            ),
            "code": code if code is not None else self._node_text(content, node),
        }

    def _extract_type_entity(self, content, path, node):
        if not self._is_global_scope_node(node):
            return None

        name_node = self._find_first_descendant(
            node,
            {"type_identifier", "identifier"},
        )
        if name_node is None:
            return None

        entity_type = "struct" if node.type == "struct_specifier" else "class"
        inheritance_node = self._find_child(node, {"base_class_clause"})
        return self._build_lightweight_entity_record(
            content=content,
            path=path,
            node=node,
            entity_type=entity_type,
            symbol_name=self._node_text(content, name_node).strip(),
            return_type=entity_type,
            parameters=self._node_text(content, inheritance_node).strip() if inheritance_node else "",
        )

    def _extract_enum_entity(self, content, path, node):
        if not self._is_global_scope_node(node):
            return None

        name_node = self._find_first_descendant(
            node,
            {"type_identifier", "identifier"},
        )
        if name_node is None:
            return None

        return self._build_lightweight_entity_record(
            content=content,
            path=path,
            node=node,
            entity_type="enum",
            symbol_name=self._node_text(content, name_node).strip(),
            return_type="enum",
            parent_symbol=self._class_parent_for_node(content, node),
        )

    def _extract_namespace_entity(self, content, path, node):
        namespace_name = self._namespace_entity_name(content, node)
        parent_namespace = self._namespace_path_for_node(content, node)
        full_namespace = "::".join(
            part for part in (parent_namespace, namespace_name) if part
        )
        display_name = full_namespace or namespace_name
        namespace_header = self._namespace_declaration_preview(content, node)
        return self._build_lightweight_entity_record(
            content=content,
            path=path,
            node=node,
            entity_type="namespace",
            symbol_name=namespace_name.split("::")[-1],
            return_type="namespace",
            parent_symbol=parent_namespace,
            namespace_path=display_name,
            code=namespace_header,
        )

    def _namespace_declaration_preview(self, content, node):
        body = self._find_child(node, {"declaration_list"})
        header_end = body.start_byte if body is not None else node.end_byte
        namespace_header = content[node.start_byte:header_end].strip()
        if not namespace_header.endswith("{"):
            namespace_header = namespace_header.rstrip() + " {"
        return namespace_header + " ... }"

    def _extract_alias_entity(self, content, path, node):
        if not self._is_global_scope_node(node):
            return None

        code = self._node_text(content, node).strip()
        match = re.search(r"\busing\s+([A-Za-z_][A-Za-z0-9_]*)\s*=", code)
        if not match:
            match = re.search(r"\btypedef\b.*\(\s*\*\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)", code)
        if not match:
            match = re.search(
                r"\btypedef\b.+\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?\s*;?\s*$",
                code,
            )
        if not match:
            return None

        return self._build_lightweight_entity_record(
            content=content,
            path=path,
            node=node,
            entity_type="type_alias",
            symbol_name=match.group(1),
            return_type="type_alias",
            code=code,
        )

    def _extract_function_declaration(self, content, path, node):
        if not self._is_global_scope_node(node):
            return None

        declarator = self._find_first_descendant(
            node,
            {"function_declarator", "reference_declarator"},
        )
        if declarator is None or self._find_first_descendant(node, {"compound_statement"}):
            return None

        name_node = self._find_first_descendant(
            declarator,
            {"identifier", "field_identifier", "qualified_identifier"},
        )
        if name_node is None:
            return None

        parameters = self._find_first_descendant(declarator, {"parameter_list"})
        raw_name = self._node_text(content, name_node).strip()
        symbol_name, parent_symbol, class_name = self._split_qualified_name(raw_name)
        namespace_path = (
            self._namespace_path_for_node(content, node)
            or self._namespace_from_qualified_name(raw_name)
        )
        qualified_symbol_name = self._build_qualified_symbol_name(
            raw_name,
            namespace_path,
            parent_symbol,
            symbol_name or raw_name,
        )

        record = self._build_lightweight_entity_record(
            content=content,
            path=path,
            node=node,
            entity_type="function_declaration",
            symbol_name=symbol_name or raw_name,
            return_type=self._extract_type_prefix(content, node, declarator),
            parameters=self._node_text(content, parameters).strip("() \n\t") if parameters else "",
            parent_symbol=parent_symbol,
            namespace_path=namespace_path,
            code=self._node_text(content, node).strip(),
        )
        record["class_name"] = class_name
        record["qualified_symbol_name"] = qualified_symbol_name
        return record

    def _extract_global_variable(self, content, path, node):
        if not self._is_global_scope_node(node):
            return None
        if self._find_first_descendant(
            node,
            {
                "function_declarator",
                "class_specifier",
                "struct_specifier",
                "enum_specifier",
            },
        ):
            return None

        code = self._node_text(content, node).strip()
        if code.startswith(("typedef ", "using ")):
            return None

        symbol_name = self._extract_declared_variable_name(content, node)
        if not symbol_name:
            return None

        return self._build_lightweight_entity_record(
            content=content,
            path=path,
            node=node,
            entity_type="global_variable",
            symbol_name=symbol_name,
            return_type="global_variable",
            code=code,
        )

    def _extract_declared_variable_name(self, content, node):
        code = self._node_text(content, node).strip().rstrip(";")
        if not code:
            return ""
        first_decl = code.split(",", 1)[0]
        first_decl = first_decl.split("=", 1)[0].strip()
        candidates = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", first_decl)
        if not candidates:
            return ""
        return candidates[-1]

    def _extract_type_prefix(self, content, node, declarator):
        if declarator.start_byte <= node.start_byte:
            return ""
        return content[node.start_byte : declarator.start_byte].strip()

    def _build_function_record(
        self,
        content,
        path,
        raw_name,
        return_type,
        parameters,
        code,
        start_index,
        namespace_path="",
    ):
        file_path = Path(path)
        symbol_name, parent_symbol, class_name = self._split_qualified_name(raw_name)
        namespace_path = namespace_path or self._namespace_from_qualified_name(raw_name)
        qualified_symbol_name = self._build_qualified_symbol_name(
            raw_name,
            namespace_path,
            parent_symbol,
            symbol_name or raw_name,
        )

        return {
            "path": path,
            "file": path,
            "file_name": file_path.name,
            "base_name": file_path.stem,
            "language": "cpp",
            "source_type": "cpp",
            "entity_type": "function_definition",
            "chunk_type": "function_definition",
            "symbol_name": symbol_name or raw_name,
            "function_name": symbol_name or raw_name,
            "parent_symbol": parent_symbol,
            "class_name": class_name,
            "return_type": return_type,
            "parameters": parameters,
            "section_path": parent_symbol,
            "namespace_path": namespace_path,
            "qualified_symbol_name": qualified_symbol_name,
            "chunk_index": 1,
            "total_chunks": 1,
            "leading_comment": self.comment_extractor.extract_leading_comment(
                content,
                start_index,
            ),
            "code": code,
        }

    #Takes function_definition node and tries to pull out:
    #   function name, return type, parameters, full src code, file path 
    def _extract_function_from_node(self, content, path, node):
        declarator = self._find_child(node, {"function_declarator", "reference_declarator"})
        body = self._find_child(node, {"compound_statement"})

        if declarator is None or body is None:
            return None

        identifier = self._find_first_descendant(
            declarator,
            {"identifier", "field_identifier", "qualified_identifier"},
        )
        parameters = self._find_first_descendant(declarator, {"parameter_list"})

        if identifier is None:
            return None

        type_node = None
        for child in node.children:
            if child == declarator or child == body:
                continue
            if child.type == "storage_class_specifier":
                continue
            type_node = child
            break

        raw_name = self._node_text(content, identifier).strip()
        return_type = self._node_text(content, type_node).strip() if type_node else ""
        parameter_text = self._node_text(content, parameters).strip("() \n\t") if parameters else ""

        return self._build_function_record(
            content=content,
            path=path,
            raw_name=raw_name,
            return_type=return_type,
            parameters=parameter_text,
            code=self._node_text(content, node),
            start_index=node.start_byte,
            namespace_path=self._namespace_path_for_node(content, node),
        )

    def extract_functions(self, files):
        functions = []

        for file in files:
            content = file["content"]
            path = file["path"]
            tree = self._parser.parse(bytes(content, "utf-8"))
            file_functions = []
            seen_entities = set()

            for node in self._walk(tree.root_node):
                entity = None
                if node.type == "function_definition":
                    entity = self._extract_function_from_node(content, path, node)
                elif node.type in {"class_specifier", "struct_specifier"}:
                    entity = self._extract_type_entity(content, path, node)
                elif node.type == "enum_specifier":
                    entity = self._extract_enum_entity(content, path, node)
                elif node.type == "namespace_definition":
                    entity = self._extract_namespace_entity(content, path, node)
                elif node.type in {"alias_declaration", "type_definition"}:
                    entity = self._extract_alias_entity(content, path, node)
                elif node.type == "declaration":
                    entity = self._extract_function_declaration(content, path, node)
                    if entity is None:
                        entity = self._extract_alias_entity(content, path, node)
                    if entity is None:
                        entity = self._extract_global_variable(content, path, node)

                if entity is not None:
                    self._append_unique_entity(file_functions, seen_entities, entity)

            file_leading_comment = self.comment_extractor.extract_top_of_file_comment(content)
            if file_leading_comment:
                attach_top_of_file_comment_to_first_function(file_functions, file_leading_comment)

            functions.extend(file_functions)

        return functions

#Function to initialize the choosen Parser Type.
def create_cpp_parser(parser_type):
    if parser_type == "tree_sitter":
        return TreeSitterParser()

    raise ValueError(
        f"Unsupported parser type: {parser_type}. Only 'tree_sitter' is supported."
    )
