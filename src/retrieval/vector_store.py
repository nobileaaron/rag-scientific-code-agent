import numpy as np


class VectorStore:

    def __init__(self, dimension):
        self.dimension = dimension
        self.vectors = np.empty((0, dimension), dtype="float32")
        #so that we can recover the corresponding chunk from the vector we need
        self.metadata = []

    def add(self, embeddings, chunks):
        #transform embedding vector into type float32
        vectors = np.array(embeddings).astype("float32")
        if vectors.ndim != 2 or vectors.shape[1] != self.dimension:
            raise ValueError(
                f"Expected embeddings with shape (n, {self.dimension}), got {vectors.shape}."
            )
        self.vectors = np.vstack([self.vectors, vectors])
        self.metadata.extend(chunks)

    def search(self, query_vector, k=5):
        #embeded prompt of user = query vector -> turn to float32
        #k...amount of neigherst search results returned.
        if len(self.metadata) == 0:
            return []
        query_vector = np.array(query_vector, dtype="float32")
        if query_vector.shape != (self.dimension,):
            raise ValueError(
                f"Expected query vector with shape ({self.dimension},), got {query_vector.shape}."
            )

        # Brute-force L2 similarity is sufficient for the current dataset size.
        distances = np.linalg.norm(self.vectors - query_vector, axis=1)
        nearest = np.argsort(distances)[:k]

        results = [self.metadata[i] for i in nearest]

        return results
