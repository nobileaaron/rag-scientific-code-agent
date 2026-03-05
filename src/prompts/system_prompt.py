from langchain.prompts import ChatPromptTemplate

code_explanation_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a scientific C++ code analysis assistant. Answer only based on the provided code context."
    ),
    (
        "user",
        """
Use the following C++ code context to answer the question.

Relevant Code:
{context}

Question:
{question}

Explain clearly how the algorithm works.
"""
    )
])