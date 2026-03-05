

class Retriever:

    def __init__(self, embedder, vector_store):
        self.embedder = embedder
        self.vector_store = vector_store

    def retrieve(self, query, k=5):

        # 1 embed the query
        query_embedding = self.embedder.query_embed(query)

        # 2 search the vector store
        results = self.vector_store.search(query_embedding, k)

        return results