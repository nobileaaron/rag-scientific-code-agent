# Ollama Modelfiles (evaluation)

These are [Ollama Modelfiles](https://github.com/ollama/ollama/blob/main/docs/modelfile.md)
used by the **Claude Code evaluation track** (see
[`../CLAUDE_CODE_EVAL.md`](../CLAUDE_CODE_EVAL.md)). Each one re-wraps a base model
with a 32k context window so the Claude Code system prompt, tool schemas, and the
IPPL files the model reads all fit:

```
FROM qwen2.5-coder:32b-instruct-q4_K_M
PARAMETER num_ctx 32768
```

| Modelfile | Base model |
| --- | --- |
| `Modelfile.qwen25_7b_cc`  | `qwen2.5-coder:7b-instruct-q4_K_M` |
| `Modelfile.qwen25_32b_cc` | `qwen2.5-coder:32b-instruct-q4_K_M` |
| `Modelfile.qwen35_9b_cc`  | `qwen3.5:9b` |
| `Modelfile.gemma4_12b_cc` | `gemma4:12b` |

## When you need these

The eval harness usually sets `num_ctx` directly in
[`../../../litellm_ollama_config.yaml`](../../../litellm_ollama_config.yaml), so you
do **not** need these for the default `run_eval_ssh.sh` flow. Use them when you want a
**named Ollama model with the larger context baked in** — e.g. to run a model
directly, or on a setup where the proxy-level `num_ctx` override isn't applied.

Build a named model from one of them with `ollama create`:

```bash
# from the repo root
ollama create qwen35_9b_cc -f docs/evaluations/modelfiles/Modelfile.qwen35_9b_cc
```

Adjust the `FROM` line if your local Ollama tag for that base model differs
(`ollama list`).
