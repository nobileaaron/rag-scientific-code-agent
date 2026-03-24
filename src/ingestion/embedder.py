#embedder.py embeds chunks into vector


def _require_ollama():
    try:
        import ollama
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependency 'ollama'. Install project dependencies with "
            "'pip install -r requirements.txt'."
        ) from exc
    return ollama



class Embedder:
    def __init__(self):
        self.transformer_model = None
        self.ollama_model = "nomic-embed-text"

    def transformer_embed(self, chunks):
        if self.transformer_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ModuleNotFoundError as exc:
                raise ModuleNotFoundError(
                    "Missing optional dependency 'sentence-transformers'. "
                    "Install it with 'pip install sentence-transformers' to use "
                    "transformer-based embeddings."
                ) from exc
            self.transformer_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self.transformer_model.encode(chunks["code"])

    def ollama_embed(self, chunks):
        ollama = _require_ollama()
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
        ollama = _require_ollama()
        response = ollama.embeddings(
            model= self.ollama_model,
            prompt= text
        )
        return response["embedding"]



