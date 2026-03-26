import re
from collections import defaultdict


class TreeSitterCallGraphBuilder:
    def __init__(self, symbol_records):
        try:
            from tree_sitter import Parser
            from tree_sitter_languages import get_language
        except ImportError as exc:
            raise ImportError(
                "Tree-sitter call graph extraction requires 'tree_sitter' and "
                "'tree_sitter_languages' to be installed."
            ) from exc

        self._parser = Parser()
        language = get_language("cpp")
        if hasattr(self._parser, "set_language"):
            self._parser.set_language(language)
        else:
            self._parser.language = language
        self.symbol_records = symbol_records
        self.callable_types = {
            "function_definition",
            "method_definition",
            "method_declaration",
        }
        self.skip_call_names = {
            "alignof",
            "catch",
            "decltype",
            "delete",
            "for",
            "if",
            "new",
            "return",
            "sizeof",
            "static_cast",
            "dynamic_cast",
            "reinterpret_cast",
            "const_cast",
            "switch",
            "while",
        }
        self._build_symbol_indexes()

    def build(self, code_entities):
        call_edges = []
        seen_edges = set()

        for entity in code_entities:
            if entity.get("chunk_type", entity.get("entity_type", "")) not in self.callable_types:
                continue

            code = entity.get("code", "")
            if not code.strip():
                continue

            tree = self._parser.parse(code.encode("utf-8"))
            for node in self._walk(tree.root_node):
                if node.type != "call_expression":
                    continue

                function_node = node.child_by_field_name("function")
                if function_node is None:
                    function_node = self._first_named_child(node)
                if function_node is None:
                    continue

                raw_call = self._node_text(code, function_node).strip()
                if not raw_call:
                    continue

                resolution = self._resolve_call(raw_call, entity)
                edge = {
                    "caller_symbol_id": self._symbol_id(entity),
                    "caller_symbol": entity.get("symbol_name", entity.get("function_name", "")),
                    "caller_parent_symbol": entity.get(
                        "parent_symbol",
                        entity.get("class_name", ""),
                    ),
                    "caller_file_path": entity.get("path", entity.get("file", "")),
                    "caller_module_scope": self._module_scope_for_file(
                        entity.get("path", entity.get("file", "")),
                    ),
                    "caller_module_path": self._module_path_for_file(
                        entity.get("path", entity.get("file", "")),
                    ),
                    "caller_module_key": self._module_key_for_file(
                        entity.get("path", entity.get("file", "")),
                    ),
                    "raw_call": raw_call,
                    "normalized_call": resolution["normalized_call"],
                    "callee_symbol_id": resolution.get("callee_symbol_id", ""),
                    "callee_symbol": resolution.get("callee_symbol", ""),
                    "callee_parent_symbol": resolution.get("callee_parent_symbol", ""),
                    "callee_file_path": resolution.get("callee_file_path", ""),
                    "callee_module_scope": resolution.get("callee_module_scope", ""),
                    "callee_module_path": resolution.get("callee_module_path", ""),
                    "callee_module_key": resolution.get("callee_module_key", ""),
                    "resolution_type": resolution["resolution_type"],
                    "confidence": resolution["confidence"],
                    "relationship": "calls",
                }

                edge_key = (
                    edge["caller_symbol_id"],
                    edge["raw_call"],
                    edge["callee_symbol_id"],
                    edge["resolution_type"],
                )
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                call_edges.append(edge)

        return call_edges

    def _build_symbol_indexes(self):
        self.symbols_by_name = defaultdict(list)
        self.symbols_by_file_and_name = defaultdict(list)
        self.symbols_by_module_and_name = defaultdict(list)
        self.symbols_by_qualified_name = defaultdict(list)

        for symbol in self.symbol_records:
            if symbol.get("chunk_type", symbol.get("entity_type", "")) not in self.callable_types:
                continue

            symbol_name = symbol.get("symbol_name", "")
            parent_symbol = symbol.get("parent_symbol", "")
            file_path = symbol.get("file_path", "")
            module_scope = symbol.get("module_scope", "")
            module_path = symbol.get("module_path", "")
            module_key = symbol.get("module_key", "")

            if symbol_name:
                self.symbols_by_name[symbol_name].append(symbol)
                self.symbols_by_file_and_name[(file_path, symbol_name)].append(symbol)
                self.symbols_by_module_and_name[(module_key, symbol_name)].append(symbol)
            if symbol_name and parent_symbol:
                self.symbols_by_qualified_name[f"{parent_symbol}::{symbol_name}"].append(symbol)

    def _resolve_call(self, raw_call, caller_entity):
        normalized_call = self._strip_templates(raw_call)
        call_name = self._terminal_name(normalized_call)
        qualified_name = self._qualified_name(normalized_call)

        if not call_name or call_name in self.skip_call_names:
            return {
                "normalized_call": call_name or normalized_call,
                "resolution_type": "skipped_builtin_or_keyword",
                "confidence": "none",
            }

        caller_file = caller_entity.get("path", caller_entity.get("file", ""))
        caller_module = self._module_key_for_file(caller_file)

        if qualified_name in self.symbols_by_qualified_name:
            symbol = self.symbols_by_qualified_name[qualified_name][0]
            return self._resolved_edge(call_name, symbol, "exact_qualified_symbol", "high")

        file_matches = self.symbols_by_file_and_name.get((caller_file, call_name), [])
        if file_matches:
            return self._resolved_edge(call_name, file_matches[0], "same_file_symbol", "high")

        module_matches = self.symbols_by_module_and_name.get((caller_module, call_name), [])
        if module_matches:
            return self._resolved_edge(call_name, module_matches[0], "same_module_symbol", "medium")

        global_matches = self.symbols_by_name.get(call_name, [])
        if len(global_matches) == 1:
            return self._resolved_edge(call_name, global_matches[0], "unique_global_symbol", "medium")
        if len(global_matches) > 1:
            return self._resolved_edge(call_name, global_matches[0], "ambiguous_global_symbol", "low")

        return {
            "normalized_call": call_name,
            "resolution_type": "unresolved_symbol",
            "confidence": "low",
        }

    def _resolved_edge(self, normalized_call, symbol, resolution_type, confidence):
        return {
            "normalized_call": normalized_call,
            "callee_symbol_id": symbol.get("symbol_id", ""),
            "callee_symbol": symbol.get("symbol_name", ""),
            "callee_parent_symbol": symbol.get("parent_symbol", ""),
            "callee_file_path": symbol.get("file_path", ""),
            "callee_module_scope": symbol.get("module_scope", ""),
            "callee_module_path": symbol.get("module_path", ""),
            "callee_module_key": symbol.get("module_key", ""),
            "resolution_type": resolution_type,
            "confidence": confidence,
        }

    def _strip_templates(self, raw_call):
        previous = None
        cleaned = raw_call.strip()
        while previous != cleaned:
            previous = cleaned
            cleaned = re.sub(r"<[^<>]*>", "", cleaned)
        return cleaned.strip()

    def _terminal_name(self, call_text):
        parts = re.split(r"::|->|\.", call_text)
        return parts[-1].strip() if parts else call_text.strip()

    def _qualified_name(self, call_text):
        if "::" not in call_text:
            return ""
        parts = [part.strip() for part in call_text.split("::") if part.strip()]
        if len(parts) < 2:
            return ""
        return "::".join(parts[-2:])

    def _symbol_id(self, entity):
        file_path = entity.get("path", entity.get("file", ""))
        symbol_name = entity.get("symbol_name", entity.get("function_name", ""))
        parent_symbol = entity.get("parent_symbol", entity.get("class_name", ""))
        entity_type = entity.get("entity_type", entity.get("chunk_type", "entity"))
        return f"{file_path}::{parent_symbol}::{symbol_name}::{entity_type}"

    def _module_path_for_file(self, file_path):
        path_text = file_path.replace("\\", "/")
        marker = "/src/"
        if marker in path_text:
            relative = path_text.split(marker, 1)[1]
            parent = "/".join(relative.split("/")[:-1])
            return parent or "root"

        root_marker = "/data/raw/ippl/"
        if root_marker in path_text:
            relative = path_text.split(root_marker, 1)[1]
            parent = "/".join(relative.split("/")[:-1])
            return parent or "root"

        parts = path_text.split("/")
        if len(parts) <= 1:
            return "root"
        return "/".join(parts[:-1]) or "root"

    def _module_scope_for_file(self, file_path):
        path_text = file_path.replace("\\", "/")
        if "/src/" in path_text:
            return "source"
        for scope in ("test", "unit_tests", "ci", "examples", "doc", "alpine"):
            marker = f"/{scope}/"
            if marker in path_text:
                return scope
        return "repo"

    def _module_key_for_file(self, file_path):
        return f"{self._module_scope_for_file(file_path)}:{self._module_path_for_file(file_path)}"

    def _node_text(self, code, node):
        return code[node.start_byte : node.end_byte]

    def _first_named_child(self, node):
        for child in node.children:
            if child.is_named:
                return child
        return None

    def _walk(self, node):
        yield node
        for child in node.children:
            yield from self._walk(child)
