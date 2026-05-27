from pathlib import Path

from src.ingestion.code.comment_extractor import CommentExtractor


def attach_top_of_file_comment_to_primary(file_entities, file_leading_comment):
    if not file_entities or not file_leading_comment:
        return

    primary = None
    for entity in file_entities:
        if entity.get("entity_type") not in {"class", "struct"}:
            continue
        if entity.get("symbol_name") == entity.get("base_name"):
            primary = entity
            break
    if primary is None:
        for entity in file_entities:
            if entity.get("entity_type") in {"class", "struct"}:
                primary = entity
                break
    if primary is None:
        primary = file_entities[0]

    existing = primary.get("leading_comment", "")
    if existing and file_leading_comment in existing:
        return
    if existing:
        primary["leading_comment"] = file_leading_comment + "\n\n" + existing
    else:
        primary["leading_comment"] = file_leading_comment


class TreeSitterHeaderParser:
    def __init__(self):
        try:
            from tree_sitter_languages import get_language
            from tree_sitter import Parser
        except ImportError as exc:
            raise ImportError(
                "Tree-sitter header parser requested, but 'tree_sitter' and "
                "'tree_sitter_languages' are not installed."
            ) from exc

        self.header_extensions = {".h", ".hpp"}
        self._parser = Parser()
        language = get_language("cpp")
        if hasattr(self._parser, "set_language"):
            self._parser.set_language(language)
        else:
            self._parser.language = language
        self.comment_extractor = CommentExtractor()

    def extract_entities(self, files):
        entities = []

        for file in files:
            path = Path(file["path"])
            if path.suffix not in self.header_extensions:
                continue

            content = file["content"]
            tree = self._parser.parse(content.encode("utf-8"))
            file_entities = []
            seen_entities = set()

            for node in self._walk(tree.root_node):
                if node.type in {"class_specifier", "struct_specifier"}:
                    entity = self._extract_type_entity(content, file["path"], node)
                    if entity is None:
                        continue

                    self._append_unique_entity(file_entities, seen_entities, entity)
                    self._extend_unique_entities(
                        file_entities,
                        seen_entities,
                        self._extract_member_entities(content, file["path"], entity["name"], node),
                    )
                elif node.type == "function_definition":
                    entity = self._extract_free_function_definition(content, file["path"], node)
                    if entity is not None:
                        self._append_unique_entity(file_entities, seen_entities, entity)

            file_leading_comment = self.comment_extractor.extract_top_of_file_comment(content)
            if file_leading_comment:
                attach_top_of_file_comment_to_primary(file_entities, file_leading_comment)

            entities.extend(file_entities)

        return entities

    def _extract_type_entity(self, content, path, node):
        name_node = self._find_first_descendant(
            node,
            {"type_identifier", "identifier"},
        )
        body_node = self._find_child(node, {"field_declaration_list"})

        if name_node is None or body_node is None:
            return None

        entity_type = "struct" if node.type == "struct_specifier" else "class"
        inheritance_node = self._find_child(node, {"base_class_clause"})

        return {
            "path": path,
            "file": path,
            "file_name": Path(path).name,
            "base_name": Path(path).stem,
            "language": "cpp",
            "source_type": "header",
            "chunk_type": entity_type,
            "symbol_name": self._node_text(content, name_node).strip(),
            "parent_symbol": self._node_text(content, name_node).strip(),
            "entity_type": entity_type,
            "function_name": self._node_text(content, name_node).strip(),
            "name": self._node_text(content, name_node).strip(),
            "class_name": self._node_text(content, name_node).strip(),
            "return_type": entity_type,
            "parameters": self._node_text(content, inheritance_node).strip() if inheritance_node else "",
            "section_path": self._node_text(content, name_node).strip(),
            "namespace_path": self._node_text(content, name_node).strip(),
            "chunk_index": 1,
            "total_chunks": 1,
            "leading_comment": self.comment_extractor.extract_leading_comment(
                content,
                node.start_byte,
            ),
            "code": self._node_text(content, node),
        }

    def _extract_member_entities(self, content, path, class_name, type_node):
        members = []
        body_node = self._find_child(type_node, {"field_declaration_list"})

        if body_node is None:
            return members

        for child in body_node.children:
            if child.type == "function_definition":
                member = self._extract_method_definition(content, path, class_name, child)
                if member is not None:
                    members.append(member)
            elif child.type == "field_declaration":
                member = self._extract_method_declaration(content, path, class_name, child)
                if member is not None:
                    members.append(member)

        return members

    def _extract_method_definition(self, content, path, class_name, node):
        declarator = self._find_first_descendant(
            node,
            {"function_declarator", "reference_declarator"},
        )
        body = self._find_child(node, {"compound_statement"})

        if declarator is None or body is None:
            return None

        name_node = self._find_first_descendant(
            declarator,
            {"identifier", "field_identifier", "qualified_identifier"},
        )
        parameters = self._find_first_descendant(declarator, {"parameter_list"})

        if name_node is None:
            return None

        return {
            "path": path,
            "file": path,
            "file_name": Path(path).name,
            "base_name": Path(path).stem,
            "language": "cpp",
            "source_type": "header",
            "chunk_type": "method_definition",
            "symbol_name": self._node_text(content, name_node).strip(),
            "parent_symbol": class_name,
            "entity_type": "method_definition",
            "function_name": self._node_text(content, name_node).strip(),
            "name": self._node_text(content, name_node).strip(),
            "class_name": class_name,
            "return_type": self._extract_type_prefix(content, node, declarator),
            "parameters": self._node_text(content, parameters).strip("() \n\t") if parameters else "",
            "section_path": class_name,
            "namespace_path": class_name,
            "chunk_index": 1,
            "total_chunks": 1,
            "leading_comment": self.comment_extractor.extract_leading_comment(
                content,
                node.start_byte,
            ),
            "code": self._node_text(content, node),
        }

    def _extract_method_declaration(self, content, path, class_name, node):
        declarator = self._find_first_descendant(
            node,
            {"function_declarator", "reference_declarator"},
        )
        if declarator is None:
            return None

        name_node = self._find_first_descendant(
            declarator,
            {"identifier", "field_identifier", "qualified_identifier"},
        )
        parameters = self._find_first_descendant(declarator, {"parameter_list"})

        if name_node is None:
            return None

        return {
            "path": path,
            "file": path,
            "file_name": Path(path).name,
            "base_name": Path(path).stem,
            "language": "cpp",
            "source_type": "header",
            "chunk_type": "method_declaration",
            "symbol_name": self._node_text(content, name_node).strip(),
            "parent_symbol": class_name,
            "entity_type": "method_declaration",
            "function_name": self._node_text(content, name_node).strip(),
            "name": self._node_text(content, name_node).strip(),
            "class_name": class_name,
            "return_type": self._extract_type_prefix(content, node, declarator),
            "parameters": self._node_text(content, parameters).strip("() \n\t") if parameters else "",
            "section_path": class_name,
            "namespace_path": class_name,
            "chunk_index": 1,
            "total_chunks": 1,
            "leading_comment": self.comment_extractor.extract_leading_comment(
                content,
                node.start_byte,
            ),
            "code": self._node_text(content, node).strip(),
        }

    def _extract_free_function_definition(self, content, path, node):
        declarator = self._find_first_descendant(
            node,
            {"function_declarator", "reference_declarator"},
        )
        body = self._find_child(node, {"compound_statement"})

        if declarator is None or body is None:
            return None

        qualified_name_node = self._find_first_descendant(
            declarator,
            {"qualified_identifier"},
        )
        if qualified_name_node is None:
            return None

        name_node = self._find_first_descendant(
            declarator,
            {"identifier", "field_identifier"},
        )
        parameters = self._find_first_descendant(declarator, {"parameter_list"})

        if name_node is None:
            return None

        qualified_name = self._node_text(content, qualified_name_node).strip()
        return {
            "path": path,
            "file": path,
            "file_name": Path(path).name,
            "base_name": Path(path).stem,
            "language": "cpp",
            "source_type": "header",
            "chunk_type": "method_definition",
            "parent_symbol": self._extract_parent_symbol(qualified_name),
            "entity_type": "method_definition",
            "symbol_name": self._node_text(content, name_node).strip(),
            "function_name": self._node_text(content, name_node).strip(),
            "name": self._node_text(content, name_node).strip(),
            "class_name": self._extract_parent_symbol(qualified_name),
            "return_type": self._extract_type_prefix(content, node, declarator),
            "parameters": self._node_text(content, parameters).strip("() \n\t") if parameters else "",
            "section_path": self._extract_parent_symbol(qualified_name),
            "namespace_path": self._extract_parent_symbol(qualified_name),
            "chunk_index": 1,
            "total_chunks": 1,
            "leading_comment": self.comment_extractor.extract_leading_comment(
                content,
                node.start_byte,
            ),
            "code": self._node_text(content, node),
        }

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

    def _extend_unique_entities(self, entities, seen_entities, new_entities):
        for entity in new_entities:
            self._append_unique_entity(entities, seen_entities, entity)

    def _extract_parent_symbol(self, qualified_name):
        qualified_parts = [part for part in qualified_name.split("::") if part]
        if len(qualified_parts) < 2:
            return ""
        return qualified_parts[-2]

    def _extract_type_prefix(self, content, node, declarator):
        if declarator.start_byte <= node.start_byte:
            return ""
        return self._node_text(
            content,
            _SliceNode(node.start_byte, declarator.start_byte),
        ).strip()

    def _node_text(self, content, node):
        return content[node.start_byte : node.end_byte]

    def _walk(self, node):
        yield node
        for child in node.children:
            yield from self._walk(child)

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


class _SliceNode:
    def __init__(self, start_byte, end_byte):
        self.start_byte = start_byte
        self.end_byte = end_byte


def create_header_parser(parser_type):
    if parser_type == "tree_sitter":
        return TreeSitterHeaderParser()

    raise ValueError(
        f"Unsupported parser type: {parser_type}. Only 'tree_sitter' is supported."
    )
