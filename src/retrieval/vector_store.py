import faiss
import numpy as np


class VectorStore:

    def __init__(self, dimension):
        self.dimension = dimension
        #L2 distance similarity search
        self.index = faiss.IndexFlatL2(dimension)

        #so that we can recover the corresponding chunk from the vector we need
        self.metadata = []

    def add(self, embeddings, chunks):
        #transform embedding vector into type float32
        vectors = np.array(embeddings).astype("float32")
        self.index.add(vectors)
        self.metadata.extend(chunks)

    def search(self, query_vector, k=5):
        #embeded prompt of user = query vector -> turn to float32
        #k...amount of neigherst search results returned.
        query_vector = np.array([query_vector]).astype("float32")
        #distances = vector L2 distances away from the vector (rising)

        distances, indices = self.index.search(query_vector, k)

        results = [self.metadata[i] for i in indices[0]]

        return results