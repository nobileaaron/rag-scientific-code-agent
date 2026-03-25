from pathlib import Path


class StructuralExpander:
    # adjust to "mode_1_minimal", "mode_2_balanced", or "mode_3_broad" later.
    DEFAULT_MODE = "mode_2_balanced"

    EXPANSION_PROFILES = {
        "mode_1_minimal": {
            "max_total_expansions": 4,
            "function_to_file_level": True,
            "function_to_call_chain": True,
            "function_to_module_level": False,
            "file_to_module_level": True,
            "file_to_symbol_chunks": 1,
            "module_to_file_level": 1,
            "call_chain_to_function": True,
            "call_chain_to_file_level": True,
            "call_chain_to_module_level": False,
        },
        "mode_2_balanced": {
            "max_total_expansions": 8,
            "function_to_file_level": True,
            "function_to_call_chain": True,
            "function_to_module_level": True,
            "file_to_module_level": True,
            "file_to_symbol_chunks": 2,
            "module_to_file_level": 2,
            "call_chain_to_function": True,
            "call_chain_to_file_level": True,
            "call_chain_to_module_level": True,
        },
        "mode_3_broad": {
            "max_total_expansions": 12,
            "function_to_file_level": True,
            "function_to_call_chain": True,
            "function_to_module_level": True,
            "file_to_module_level": True,
            "file_to_symbol_chunks": 3,
            "module_to_file_level": 3,
            "call_chain_to_function": True,
            "call_chain_to_file_level": True,
            "call_chain_to_module_level": True,
        },
    }

    def __init__(self, metadata, mode=None):
        # adjust to StructuralExpander(..., mode="mode_1_minimal") or other modes later.
        self.mode = mode or self.DEFAULT_MODE
        self.metadata = metadata
        self._build_indexes()

    def expand(self, query, seed_chunks, mode=None):
        active_mode = mode or self.mode
        profile = self.EXPANSION_PROFILES[active_mode]
        seed_keys = {self._chunk_key(chunk) for chunk in seed_chunks}
        expanded_chunks = []
        expanded_keys = set()
        expansion_reasons = []

        for seed in seed_chunks:
            if len(expanded_chunks) >= profile["max_total_expansions"]:
                break

            for related_chunk, reason in self._expand_seed(seed, profile):
                chunk_key = self._chunk_key(related_chunk)
                if chunk_key in seed_keys or chunk_key in expanded_keys:
                    continue

                expanded_keys.add(chunk_key)
                expanded_chunks.append(
                    {
                        **related_chunk,
                        "expansion_reason": reason,
                    }
                )
                expansion_reasons.append(reason)

                if len(expanded_chunks) >= profile["max_total_expansions"]:
                    break

        return {
            "chunks": expanded_chunks,
            "diagnostics": {
                "mode": active_mode,
                "count": len(expanded_chunks),
                "reasons": expansion_reasons,
            },
        }

    def _expand_seed(self, seed, profile):
        entity_level = seed.get("entity_level", "")
        if entity_level == "file_level":
            yield from self._expand_file_level(seed, profile)
            return
        if entity_level == "module_level":
            yield from self._expand_module_level(seed, profile)
            return
        if entity_level == "call_chain_level":
            yield from self._expand_call_chain_level(seed, profile)
            return

        yield from self._expand_function_level(seed, profile)

    def _expand_function_level(self, seed, profile):
        file_path = seed.get("path", seed.get("file", ""))
        module_key = seed.get("module_key", "")
        symbol_key = self._symbol_key(seed)

        if profile["function_to_file_level"] and file_path in self.file_level_by_path:
            yield self.file_level_by_path[file_path], "function_to_file_level"

        if profile["function_to_call_chain"] and symbol_key in self.call_chain_by_symbol_key:
            yield self.call_chain_by_symbol_key[symbol_key], "function_to_call_chain"

        if profile["function_to_module_level"] and module_key in self.module_level_by_key:
            yield self.module_level_by_key[module_key], "function_to_module_level"

    def _expand_file_level(self, seed, profile):
        module_key = seed.get("module_key", "")
        file_path = seed.get("path", seed.get("file", ""))

        if profile["file_to_module_level"] and module_key in self.module_level_by_key:
            yield self.module_level_by_key[module_key], "file_to_module_level"

        symbol_chunk_limit = profile["file_to_symbol_chunks"]
        if symbol_chunk_limit <= 0:
            return

        symbol_chunks = self.function_chunks_by_file.get(file_path, [])
        for chunk in symbol_chunks[:symbol_chunk_limit]:
            yield chunk, "file_to_symbol_chunk"

    def _expand_module_level(self, seed, profile):
        file_limit = profile["module_to_file_level"]
        if file_limit <= 0:
            return

        for file_path in seed.get("contained_file_paths", [])[:file_limit]:
            if file_path in self.file_level_by_path:
                yield self.file_level_by_path[file_path], "module_to_file_level"

    def _expand_call_chain_level(self, seed, profile):
        file_path = seed.get("path", seed.get("file", ""))
        module_key = seed.get("module_key", "")
        symbol_key = self._symbol_key(seed)

        if profile["call_chain_to_function"]:
            function_chunks = self.function_chunks_by_symbol_key.get(symbol_key, [])
            for chunk in function_chunks[:1]:
                yield chunk, "call_chain_to_function"

        if profile["call_chain_to_file_level"] and file_path in self.file_level_by_path:
            yield self.file_level_by_path[file_path], "call_chain_to_file_level"

        if profile["call_chain_to_module_level"] and module_key in self.module_level_by_key:
            yield self.module_level_by_key[module_key], "call_chain_to_module_level"

    def _build_indexes(self):
        self.file_level_by_path = {}
        self.module_level_by_key = {}
        self.call_chain_by_symbol_key = {}
        self.function_chunks_by_symbol_key = {}
        self.function_chunks_by_file = {}

        for chunk in self.metadata:
            entity_level = chunk.get("entity_level", "")
            if entity_level == "file_level":
                self.file_level_by_path[chunk.get("path", chunk.get("file", ""))] = chunk
                continue

            if entity_level == "module_level":
                self.module_level_by_key[chunk.get("module_key", "")] = chunk
                continue

            if entity_level == "call_chain_level":
                self.call_chain_by_symbol_key[self._symbol_key(chunk)] = chunk
                continue

            if chunk.get("chunk_type", chunk.get("entity_type", "")) in {
                "function_definition",
                "method_definition",
                "method_declaration",
            }:
                symbol_key = self._symbol_key(chunk)
                self.function_chunks_by_symbol_key.setdefault(symbol_key, []).append(chunk)
                file_path = chunk.get("path", chunk.get("file", ""))
                self.function_chunks_by_file.setdefault(file_path, []).append(chunk)

        for symbol_key, chunks in self.function_chunks_by_symbol_key.items():
            self.function_chunks_by_symbol_key[symbol_key] = self._sort_function_chunks(chunks)

        for file_path, chunks in self.function_chunks_by_file.items():
            self.function_chunks_by_file[file_path] = self._sort_function_chunks(chunks)

    def _sort_function_chunks(self, chunks):
        return sorted(
            chunks,
            key=lambda chunk: (
                chunk.get("chunk_index", 1) != 1,
                str(chunk.get("symbol_name", chunk.get("function_name", ""))).lower(),
                chunk.get("chunk_index", 1),
            ),
        )

    def _symbol_key(self, chunk):
        return (
            chunk.get("path", chunk.get("file", "")),
            chunk.get("symbol_name", chunk.get("function_name", "")),
            chunk.get("parent_symbol", ""),
        )

    def _chunk_key(self, chunk):
        return (
            chunk.get("file", ""),
            chunk.get("symbol_name", chunk.get("function_name", "")),
            chunk.get("chunk_index", 1),
            chunk.get("code", ""),
        )
