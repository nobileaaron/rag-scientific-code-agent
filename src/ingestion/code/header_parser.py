import re
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


class RegexHeaderParser:
    def __init__(self):
        self.comment_extractor = CommentExtractor()
        self.header_extensions = {".h", ".hpp"}
        self.type_pattern = re.compile(
            r"(class|struct)\s+([A-Za-z_]\w*(?:\s*<[^;{>]+>)?)"
            r"(?:\s*:\s*([^{]+))?\s*\{",
            re.MULTILINE,
        )
        self.method_definition_pattern = re.compile(
            r"([A-Za-z_][\w:<>\s*&~]+)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:const\s*)?\{",
            re.MULTILINE,
        )
        self.method_declaration_pattern = re.compile(
            r"([A-Za-z_][\w:<>\s*&~]+)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:const\s*)?;",
            re.MULTILINE,
        )
        self.free_function_definition_pattern = re.compile(
            r"([A-Za-z_][\w:<>\s*&~,]+)\s+([A-Za-z_][\w:<>~]*)\s*\(([^)]*)\)\s*(?:const\s*)?\{",
            re.MULTILINE,
        )

    def extract_entities(self, files):
        entities = []

        for file in files:
            path = Path(file["path"])
            if path.suffix not in self.header_extensions:
                continue

            content = file["content"]
            file_entities = []
            seen_entities = set()
            for type_match in self.type_pattern.finditer(content):
                block_start = type_match.start()
                block_code = self._extract_block(content, block_start)
                class_name = type_match.group(2).strip()
                inherits = (type_match.group(3) or "").strip()

                self._append_unique_entity(
                    file_entities,
                    seen_entities,
                    self._build_entity(
                        content=content,
                        file_path=file["path"],
                        entity_type=type_match.group(1),
                        name=class_name,
                        code=block_code,
                        return_type=type_match.group(1),
                        parameters=inherits,
                        class_name=class_name,
                        start_index=block_start,
                    )
                )

                self._extend_unique_entities(
                    file_entities,
                    seen_entities,
                    self._extract_members(file["path"], class_name, block_code)
                )

            self._extend_unique_entities(
                file_entities,
                seen_entities,
                self._extract_free_function_definitions(file["path"], content),
            )

            file_leading_comment = self.comment_extractor.extract_top_of_file_comment(content)
            if file_leading_comment:
                attach_top_of_file_comment_to_primary(file_entities, file_leading_comment)

            entities.extend(file_entities)

        return entities

    def _extract_members(self, path, class_name, class_code):
        members = []

        for match in self.method_definition_pattern.finditer(class_code):
            member_code = self._extract_block(class_code, match.start())
            members.append(
                self._build_entity(
                    content=class_code,
                    file_path=path,
                    entity_type="method_definition",
                    name=match.group(2),
                    code=member_code,
                    return_type=match.group(1).strip(),
                    parameters=match.group(3).strip(),
                    class_name=class_name,
                    start_index=match.start(),
                )
            )

        for match in self.method_declaration_pattern.finditer(class_code):
            signature = match.group(0).strip()
            members.append(
                self._build_entity(
                    content=class_code,
                    file_path=path,
                    entity_type="method_declaration",
                    name=match.group(2),
                    code=signature,
                    return_type=match.group(1).strip(),
                    parameters=match.group(3).strip(),
                    class_name=class_name,
                    start_index=match.start(),
                )
            )

        return members

    def _build_entity(
        self,
        content,
        file_path,
        entity_type,
        name,
        code,
        return_type="",
        parameters="",
        class_name="",
        start_index=0,
    ):
        return {
            "path": file_path,
            "file": file_path,
            "file_name": Path(file_path).name,
            "base_name": Path(file_path).stem,
            "language": "cpp",
            "source_type": "header",
            "chunk_type": entity_type,
            "symbol_name": name,
            "parent_symbol": class_name,
            "entity_type": entity_type,
            "name": name,
            "function_name": name,
            "class_name": class_name,
            "return_type": return_type,
            "parameters": parameters,
            "section_path": class_name,
            "namespace_path": class_name,
            "chunk_index": 1,
            "total_chunks": 1,
            "leading_comment": self.comment_extractor.extract_leading_comment(
                content,
                start_index,
            ),
            "code": code,
        }

    def _append_unique_entity(self, entities, seen_entities, entity):
        entity_key = (
            entity["file"],
            entity["entity_type"],
            entity["symbol_name"],
            entity["code"],
        )
        if entity_key in seen_entities:
            return
        seen_entities.add(entity_key)
        entities.append(entity)

    def _extend_unique_entities(self, entities, seen_entities, new_entities):
        for entity in new_entities:
            self._append_unique_entity(entities, seen_entities, entity)

    def _extract_free_function_definitions(self, path, content):
        entities = []

        for match in self.free_function_definition_pattern.finditer(content):
            qualified_name = match.group(2).strip()
            if "::" not in qualified_name:
                continue

            function_code = self._extract_block(content, match.start())
            function_name = qualified_name.split("::")[-1]
            class_name = self._extract_parent_symbol(qualified_name)

            entities.append(
                self._build_entity(
                    content=content,
                    file_path=path,
                    entity_type="method_definition",
                    name=function_name,
                    code=function_code,
                    return_type=match.group(1).strip(),
                    parameters=match.group(3).strip(),
                    class_name=class_name,
                    start_index=match.start(),
                )
            )

        return entities

    def _extract_parent_symbol(self, qualified_name):
        qualified_parts = [part for part in qualified_name.split("::") if part]
        if len(qualified_parts) < 2:
            return ""
        return qualified_parts[-2]

    def _extract_block(self, content, start_index):
        brace_count = 0
        seen_open = False
        i = start_index

        while i < len(content):
            char = content[i]
            if char == "{":
                brace_count += 1
                seen_open = True
            elif char == "}":
                brace_count -= 1
                if seen_open and brace_count == 0:
                    end = i + 1
                    while end < len(content) and content[end] in {";", "\n", " "}:
                        end += 1
                    return content[start_index:end]
            i += 1

        return content[start_index:i]


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
    if parser_type == "regex":
        return RegexHeaderParser()
    if parser_type == "tree_sitter":
        return TreeSitterHeaderParser()

    raise ValueError(f"Unsupported parser type: {parser_type}")
