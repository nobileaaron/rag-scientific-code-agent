#Takes Built prompt from LLMAgent and talks to the model

import os

try:
    from langchain_community.chat_models import ChatOllama
except ImportError:
    ChatOllama = None

try:
    import ollama
except ImportError:
    ollama = None


DEFAULT_ANTHROPIC_MAX_TOKENS = 4096


def resolve_model_config(model):
    """Normalize a model entry from runtime_settings.json into a dict.

    Accepts either:
      - str: treated as an Ollama model name (backward compat with the
        original single-provider setup).
      - dict: must include ``provider`` ("ollama" or "anthropic") and
        ``name``. Additional keys are passed through as provider params
        (e.g. ``max_tokens``, ``thinking``, ``effort`` for Anthropic).
    """
    if isinstance(model, str):
        return {"provider": "ollama", "name": model, "params": {}}

    if not isinstance(model, dict):
        raise TypeError(
            f"Model config must be a string or dict, got {type(model).__name__}."
        )

    provider = model.get("provider", "ollama")
    name = model.get("name")
    if not name:
        raise ValueError(f"Model config missing 'name': {model}")

    params = {k: v for k, v in model.items() if k not in ("provider", "name")}
    return {"provider": provider, "name": name, "params": params}


def model_manifest_key(model):
    """Stable string used in the vector store manifest.

    Switching provider OR model name forces a rebuild, same as any other
    manifest change.
    """
    config = resolve_model_config(model)
    return f"{config['provider']}:{config['name']}"


class LLMWrapper:

    def __init__(self, model):
        self.config = resolve_model_config(model)
        self.provider = self.config["provider"]
        self.model_name = self.config["name"]
        self.params = self.config["params"]

        if self.provider == "ollama":
            self._init_ollama()
        elif self.provider == "anthropic":
            self._init_anthropic()
        else:
            raise ValueError(
                f"Unknown LLM provider '{self.provider}'. Expected 'ollama' or 'anthropic'."
            )

    def _init_ollama(self):
        self.llm = ChatOllama(model=self.model_name) if ChatOllama is not None else None
        if self.llm is None and ollama is None:
            raise ImportError(
                "Neither langchain_community.ChatOllama nor the 'ollama' package is "
                "available. Install one to use the ollama provider."
            )

    def _init_anthropic(self):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError(
                "The 'anthropic' package is required for the anthropic provider. "
                "Install it with `pip install anthropic`."
            ) from exc

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Export it before running the pipeline "
                "so the anthropic provider can authenticate."
            )

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.max_tokens = int(self.params.get("max_tokens", DEFAULT_ANTHROPIC_MAX_TOKENS))
        self.system_prompt = self.params.get("system")
        self.thinking = self.params.get("thinking")
        self.effort = self.params.get("effort")
        self.extra_headers = self.params.get("extra_headers")

    def generate(self, prompt):
        prompt_text = prompt["text"] if isinstance(prompt, dict) else prompt

        if self.provider == "ollama":
            return self._generate_ollama(prompt_text)
        if self.provider == "anthropic":
            return self._generate_anthropic(prompt_text)
        raise ValueError(f"Unknown provider '{self.provider}'.")

    def _generate_ollama(self, prompt_text):
        if self.llm is not None:
            response = self.llm.invoke(prompt_text)
            return response.content

        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt_text}],
        )
        return response["message"]["content"]

    def _generate_anthropic(self, prompt_text):
        request_kwargs = {
            "model": self.model_name,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt_text}],
        }
        if self.system_prompt:
            request_kwargs["system"] = self.system_prompt
        if self.thinking is not None:
            request_kwargs["thinking"] = self.thinking
        output_config = {}
        if self.effort is not None:
            output_config["effort"] = self.effort
        if output_config:
            request_kwargs["output_config"] = output_config
        if self.extra_headers:
            request_kwargs["extra_headers"] = self.extra_headers

        # Stream to avoid request timeouts on long chunk-explanation prompts.
        with self.client.messages.stream(**request_kwargs) as stream:
            final_message = stream.get_final_message()

        text_parts = [
            block.text for block in final_message.content if getattr(block, "type", None) == "text"
        ]
        return "".join(text_parts)
