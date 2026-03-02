#Step 1 
#Chunk the Cpp file

from chunker import load_cpp_file, simple_chunk

code = load_cpp_file("cpp_code/poisson_solver.cpp")

chunks = simple_chunk(code)

for i, chunk in enumerate(chunks):
    print(f"\n--- Chunk {i} ---\n")
    print(chunk)

#Step2
#Create Embeddings with Ollama
import ollama
import numpy as np

embeddings = []

for chunk in chunks:
    response = ollama.embeddings(
        model="nomic-embed-text",
        prompt=chunk
    )
    embeddings.append(response["embedding"])

print("Number of embeddings:", len(embeddings))

#Step3
#Store in FAISS

import faiss
#dimension of embedding
dimension = len(embeddings[0]) 
print("dimension of embedding", dimension)
#create search index, L2 = Euclidean Metric             
index = faiss.IndexFlatL2(dimension)

#FAISS requires: NumPy array of float32 type
vectors = np.array(embeddings).astype("float32")
#stores all chunk vectors inside FAISS
index.add(vectors)

print("FAISS index contains:", index.ntotal, "vectors")

# ============================
# Step 4 - RAG Retrieval Loop
# ============================

# Ask user for a question
user_question = input("\nAsk a question about the C++ code: ")

# 1️⃣ Embed the user question
query_response = ollama.embeddings(
    model="nomic-embed-text",
    prompt=user_question
)

query_embedding = query_response["embedding"]

# Convert to correct NumPy format for FAISS
query_vector = np.array([query_embedding]).astype("float32")

# 2️⃣ Retrieve top 3 most similar chunks
k = 3
distances, indices = index.search(query_vector, k)

# Get the actual chunk texts
retrieved_chunks = [chunks[i] for i in indices[0]]

print("\nRetrieved Chunks:\n")
for i, chunk in enumerate(retrieved_chunks):
    print(f"\n--- Retrieved Chunk {i} ---\n")
    print(chunk)

# 3️⃣ Send retrieved chunks to LLM
context = "\n\n".join(retrieved_chunks)

chat_response = ollama.chat(
    model="deepseek-coder",
    messages=[
        {
            "role": "system",
            "content": "You are a scientific C++ code analysis assistant. Answer only based on the provided code context."
        },
        {
            "role": "user",
            "content": f"""
Use the following C++ code context to answer the question.

{context}

Question:
{user_question}
"""
        }
    ]
)

# 4️⃣ Print final answer
print("\nLLM Answer:\n")
print(chat_response["message"]["content"])