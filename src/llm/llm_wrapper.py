#Takes Built prompt from LLMAgent and talks to the model

try:
    from langchain_community.chat_models import ChatOllama
except ImportError:
    ChatOllama = None
    import ollama


class LLMWrapper:

    def __init__(self, model):
        self.model = model
        self.llm = ChatOllama(model=model) if ChatOllama is not None else None

    def generate(self, prompt):
        prompt_text = prompt["text"] if isinstance(prompt, dict) else prompt

        if self.llm is not None:
            response = self.llm.invoke(prompt_text)
            return response.content

        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt_text}],
        )
        return response["message"]["content"]
