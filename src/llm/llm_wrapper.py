#Takes Built prompt from LLMAgent and talks to the model


class LLMWrapper:

    def __init__(self, model):
        try:
            from langchain_community.chat_models import ChatOllama
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "Missing dependency 'langchain-community'. Install project "
                "dependencies with 'pip install -r requirements.txt'."
            ) from exc
        self.llm = ChatOllama(model=model)

    def generate(self, prompt):

        response = self.llm.invoke(prompt)

        return response.content
