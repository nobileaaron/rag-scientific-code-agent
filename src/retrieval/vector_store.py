import faiss
import numpy as np
import json
from pathlib import Path


class VectorStore:

    def __init__(self, dimension):
        self.dimension = dimension
        #L2 distance similarity search
        self.index = faiss.IndexFlatL2(dimension)

        #so that we can recover the corresponding chunk from the vector we need
        self.metadata = []
        self.vectors = np.empty((0, dimension), dtype="float32")

    def add(self, embeddings, chunks):
        #transform embedding vector into type float32
        vectors = np.array(embeddings).astype("float32")
        self.index.add(vectors)
        if self.vectors.size == 0:
            self.vectors = vectors
        else:
            self.vectors = np.vstack([self.vectors, vectors]).astype("float32")
        #full chunk is stored as metadata: parameters, path etc..
        self.metadata.extend(chunks)

    def search(self, query_vector, k=5):
        #embeded prompt of user = query vector -> turn to float32
        #k...amount of neigherst search results returned.
        query_vector = np.array([query_vector]).astype("float32")
        #distances = vector L2 distances away from the vector (rising)

        distances, indices = self.index.search(query_vector, k)
        results = []
        for distance, index in zip(distances[0], indices[0]):
            if index < 0 or index >= len(self.metadata):
                continue
            results.append(
                {
                    "chunk": self.metadata[index],
                    "distance": float(distance),
                }
            )

        return results

    def get_chunks_by_filenames(self, file_names, query_vector=None):
        normalized_names = {
            str(file_name).strip().lower()
            for file_name in file_names
            if str(file_name).strip()
        }
        if not normalized_names:
            return []

        query_vector = (
            np.array(query_vector).astype("float32")
            if query_vector is not None
            else None
        )
        file_level_chunks = []
        matched_base_names = set()

        for index, chunk in enumerate(self.metadata):
            if chunk.get("entity_level") != "file_level":
                continue

            chunk_file_name = str(
                chunk.get("file_name", Path(chunk.get("file", "")).name)
            ).lower()
            chunk_base_name = str(
                chunk.get("base_name", Path(chunk_file_name).stem)
            ).lower()
            file_level_chunks.append(
                {
                    "index": index,
                    "chunk": chunk,
                    "file_name": chunk_file_name,
                    "base_name": chunk_base_name,
                }
            )

            if chunk_file_name in normalized_names or chunk_base_name in normalized_names:
                matched_base_names.add(chunk_base_name)

        results = []
        seen_keys = set()

        for entry in file_level_chunks:
            exact_base_match = entry["base_name"] in normalized_names
            exact_file_match = entry["file_name"] in normalized_names
            sibling_file_match = (
                entry["base_name"] in matched_base_names
                and not exact_base_match
                and not exact_file_match
            )
            if not (exact_base_match or exact_file_match or sibling_file_match):
                continue

            chunk_key = (
                entry["chunk"].get("file", ""),
                entry["chunk"].get("symbol_name", entry["chunk"].get("function_name", "")),
                entry["chunk"].get("chunk_index", 1),
                entry["chunk"].get("code", ""),
            )
            if chunk_key in seen_keys:
                continue
            seen_keys.add(chunk_key)

            distance = 0.0
            if sibling_file_match and query_vector is not None:
                distance = float(np.sum((self.vectors[entry["index"]] - query_vector) ** 2))

            results.append(
                {
                    "chunk": entry["chunk"],
                    "distance": distance,
                    "injected": True,
                }
            )

        return results

    def get_chunks_by_symbols(self, symbol_names):
        normalized_symbols = {
            str(symbol_name).strip().lower()
            for symbol_name in symbol_names
            if str(symbol_name).strip()
        }
        if not normalized_symbols:
            return []

        results = []
        for chunk in self.metadata:
            if chunk.get("entity_level") != "function_level":
                continue
            chunk_symbol = str(
                chunk.get("symbol_name", chunk.get("function_name", ""))
            ).lower()
            chunk_qualified_symbol = str(chunk.get("qualified_symbol_name", "")).lower()
            chunk_namespace = str(chunk.get("namespace_path", "")).lower()
            chunk_parent_symbol = str(chunk.get("parent_symbol", "")).lower()
            namespace_symbol = (
                f"{chunk_namespace}::{chunk_symbol}"
                if chunk_namespace and chunk_symbol
                else ""
            )
            namespace_parent_symbol = (
                f"{chunk_namespace}::{chunk_parent_symbol}::{chunk_symbol}"
                if chunk_namespace and chunk_parent_symbol and chunk_symbol
                else ""
            )
            symbol_candidates = {
                value
                for value in (
                    chunk_symbol,
                    chunk_namespace,
                    chunk_qualified_symbol,
                    namespace_symbol,
                    namespace_parent_symbol,
                )
                if value
            }
            if symbol_candidates & normalized_symbols:
                chunk_file_name = str(
                    chunk.get("file_name", Path(chunk.get("file", "")).name)
                ).lower()
                chunk_base_name = str(
                    chunk.get("base_name", Path(chunk_file_name).stem)
                ).lower()
                chunk_file_stem = (
                    chunk_file_name.rsplit(".", 1)[0]
                    if "." in chunk_file_name
                    else chunk_file_name
                )
                file_context_match = (
                    chunk_base_name in normalized_symbols
                    or chunk_file_stem in normalized_symbols
                    or chunk_file_name in normalized_symbols
                )
                symbol_is_file_subject = chunk_symbol in {
                    chunk_base_name,
                    chunk_file_stem,
                    chunk_file_name,
                }
                qualified_symbol_match = any(
                    symbol
                    for symbol in normalized_symbols
                    if "::" in symbol and symbol in symbol_candidates
                )
                distance = 0.0 if (
                    qualified_symbol_match
                    or (file_context_match and not symbol_is_file_subject)
                ) else 0.2
                results.append(
                    {
                        "chunk": chunk,
                        "distance": distance,
                        "injected": True,
                    }
                )

        results.sort(key=lambda candidate: candidate["distance"])
        return results[:2]


    def get_chunks_by_modulenames(self, module_names):
        normalized_names = {module_name.lower() for module_name in module_names}
        if not normalized_names:
            return []

        results = []
        for chunk in self.metadata:
            if chunk.get("entity_level") != "module_level":
                continue
            chunk_module_name = str(
                chunk.get("module_name", chunk.get("symbol_name", ""))
            ).lower()
            if chunk_module_name in normalized_names:
                results.append(
                    {
                        "chunk": chunk,
                        "distance": 0.0,
                        "injected": True,
                    }
                )

        return results

    def search_in_filenames(self, query_vector, file_names, k=3):
        normalized_names = {file_name.lower() for file_name in file_names}
        if not normalized_names or len(self.metadata) == 0:
            return []

        query_vector = np.array(query_vector).astype("float32")
        results = []

        for index, chunk in enumerate(self.metadata):
            if chunk.get("entity_level") != "function_level":
                continue
            chunk_file_name = str(
                chunk.get("file_name", Path(chunk.get("file", "")).name)
            ).lower()
            if chunk_file_name not in normalized_names:
                continue

            distance = float(np.sum((self.vectors[index] - query_vector) ** 2))
            results.append(
                {
                    "chunk": chunk,
                    "distance": distance,
                }
            )

        results.sort(key=lambda candidate: candidate["distance"])
        return results[:k]

    def save(self, directory, manifest=None):
        directory_path = Path(directory)
        directory_path.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(directory_path / "index.faiss"))
        np.save(directory_path / "vectors.npy", self.vectors)

        with (directory_path / "metadata.json").open("w", encoding="utf-8") as file:
            json.dump(self.metadata, file, ensure_ascii=True, indent=2)

        manifest_data = dict(manifest or {})
        manifest_data["dimension"] = self.dimension
        manifest_data["metadata_count"] = len(self.metadata)
        manifest_data["vector_count"] = int(self.vectors.shape[0])
        with (directory_path / "manifest.json").open("w", encoding="utf-8") as file:
            json.dump(manifest_data, file, ensure_ascii=True, indent=2)

    @classmethod
    def load(cls, directory):
        directory_path = Path(directory)
        manifest_path = directory_path / "manifest.json"
        metadata_path = directory_path / "metadata.json"
        vectors_path = directory_path / "vectors.npy"
        index_path = directory_path / "index.faiss"

        with manifest_path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)

        store = cls(manifest["dimension"])
        store.index = faiss.read_index(str(index_path))
        store.vectors = np.load(vectors_path).astype("float32")

        with metadata_path.open("r", encoding="utf-8") as file:
            store.metadata = json.load(file)

        return store, manifest

    @staticmethod
    def persisted_files_exist(directory):
        directory_path = Path(directory)
        required_files = [
            directory_path / "index.faiss",
            directory_path / "vectors.npy",
            directory_path / "metadata.json",
            directory_path / "manifest.json",
        ]
        return all(path.exists() for path in required_files)
