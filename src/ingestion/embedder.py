#embedder.py embeds chunks into vector
from sentence_transformers import SentenceTransformer
import ollama



class Embedder:
    def __init__(self):
        self.transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.ollama_model = "nomic-embed-text"

    def transformer_embed(self, chunks):
        return self.transformer_model.encode(chunks["code"])

    def ollama_embed(self, chunks):
        embeddings = []
        for chunk in chunks: 
            response = ollama.embeddings(
                model= self.ollama_model,
                prompt = f"""
                Function: {chunk['function_name']}
                Path: {chunk['file']}
                Code: 
                {chunk['code']}
                """
                )
            embeddings.append(response["embedding"])
        return embeddings 
    
    def query_embed(self, text):
        response = ollama.embeddings(
            model= self.ollama_model,
            prompt= text
        )
        return response["embedding"]




