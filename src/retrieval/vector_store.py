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

    def get_chunks_by_filenames(self, file_names):
        normalized_names = {file_name.lower() for file_name in file_names}
        if not normalized_names:
            return []

        results = []
        for chunk in self.metadata:
            chunk_file_name = str(
                chunk.get("file_name", Path(chunk.get("file", "")).name)
            ).lower()
            if chunk_file_name in normalized_names:
                results.append(
                    {
                        "chunk": chunk,
                        "distance": 0.0,
                        "injected": True,
                    }
                )

        return results

    def get_chunks_by_symbols(self, symbol_names):
        normalized_symbols = {symbol_name.lower() for symbol_name in symbol_names}
        if not normalized_symbols:
            return []

        results = []
        for chunk in self.metadata:
            chunk_symbol = str(
                chunk.get("symbol_name", chunk.get("function_name", ""))
            ).lower()
            if chunk_symbol in normalized_symbols:
                results.append(
                    {
                        "chunk": chunk,
                        "distance": 0.0,
                        "injected": True,
                    }
                )

        return results

    def search_in_filenames(self, query_vector, file_names, k=5):
        normalized_names = {file_name.lower() for file_name in file_names}
        if not normalized_names or len(self.metadata) == 0:
            return []

        query_vector = np.array(query_vector).astype("float32")
        results = []

        for index, chunk in enumerate(self.metadata):
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
