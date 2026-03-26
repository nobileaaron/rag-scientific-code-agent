import re
from pathlib import Path

from src.ingestion.code.comment_extractor import CommentExtractor


class RegexParser:
    def __init__(self):
        self.comment_extractor = CommentExtractor()
        self.function_pattern = re.compile(
            r"([a-zA-Z_][\w:<>\s*&]+)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*\{",
            re.MULTILINE,
        )

    def _extract_full_function(self, content, start_index):
        brace_count = 0
        i = start_index
        function_started = False

        while i < len(content):
            char = content[i]

            if char == "{":
                brace_count += 1
                function_started = True
            elif char == "}":
                brace_count -= 1

                if function_started and brace_count == 0:
                    return content[start_index : i + 1]

            i += 1

        return content[start_index:i]

    def extract_functions(self, files):
        functions = []

        for file in files:
            content = file["content"]
            path = file["path"]

            for match in self.function_pattern.finditer(content):
                start_index = match.start()
                function_code = self._extract_full_function(content, start_index)
                functions.append(
                    {
                        "path": path,
                        "file": path,
                        "file_name": Path(path).name,
                        "base_name": Path(path).stem,
                        "language": "cpp",
                        "source_type": "cpp",
                        "entity_type": "function_definition",
                        "chunk_type": "function_definition",
                        "symbol_name": match.group(2),
                        "function_name": match.group(2),
                        "parent_symbol": "",
                        "class_name": "",
                        "return_type": match.group(1),
                        "parameters": match.group(3),
                        "section_path": "",
                        "namespace_path": "",
                        "chunk_index": 1,
                        "total_chunks": 1,
                        "leading_comment": self.comment_extractor.extract_leading_comment(
                            content,
                            start_index,
                        ),
                        "code": function_code,
                    }
                )

        return functions


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

    def _build_function_record(
        self,
        content,
        path,
        raw_name,
        return_type,
        parameters,
        code,
        start_index,
    ):
        file_path = Path(path)
        symbol_name, parent_symbol, class_name = self._split_qualified_name(raw_name)

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
            "namespace_path": parent_symbol,
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
        )

    def extract_functions(self, files):
        functions = []

        for file in files:
            content = file["content"]
            path = file["path"]
            tree = self._parser.parse(bytes(content, "utf-8"))

            for node in self._walk(tree.root_node):
                if node.type != "function_definition":
                    continue

                function_data = self._extract_function_from_node(content, path, node)
                if function_data is not None:
                    functions.append(function_data)

        return functions

#Function to initialize the choosen Parser Type.
def create_cpp_parser(parser_type):
    if parser_type == "regex":
        return RegexParser()
    if parser_type == "tree_sitter":
        return TreeSitterParser()

    raise ValueError(f"Unsupported parser type: {parser_type}")
