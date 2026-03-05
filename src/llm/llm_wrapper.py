#Takes Built prompt from LLMAgent and talks to the model

from langchain_community.chat_models import ChatOllama


class LLMWrapper:

    def __init__(self, model):
        self.llm = ChatOllama(model=model)

    def generate(self, prompt):

        response = self.llm.invoke(prompt)

        return response.content