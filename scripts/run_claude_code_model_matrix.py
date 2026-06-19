#!/usr/bin/env python3
"""Run the IPPL eval question set through Claude Code against several local
(Ollama-backed) models exposed via a LiteLLM proxy.

For every configured model this drives `claude -p` once per question, letting
Claude Code explore the IPPL source under data/raw/ippl with read-only tools,
and stores the answers in docs/evaluations/answers/ in the same style as the
other eval files.

The proxy wiring (ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN) is expected to be
in the environment already — run_eval_ssh.sh sets it up. You can also export it
yourself and run this script directly.
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# (claude --model name, output-file label, ollama tag for the manifest record).
# The model name must match a `model_name` in litellm_ollama_config.yaml.
DEFAULT_MODELS = [
    ("claude-qwen25-7b-q4km", "qwen25_7b_q4km", "qwen2.5-coder:7b-instruct-q4_K_M"),
    ("claude-qwen25-32b-q4km", "qwen25_32b_q4km", "qwen2.5-coder:32b-instruct-q4_K_M"),
    ("claude-qwen35-9b", "qwen35_9b", "qwen3.5:9b"),
    ("claude-gemma4-12b", "gemma4_12b", "gemma4:12b"),
]

PROMPT_TEMPLATE = """You are answering an IPPL benchmark question.

Use only repository files under data/raw/ippl and the repository documentation.
Explore the source with your read-only tools to ground the answer in concrete
files and symbols. Cite the files/symbols you relied on.
If the repository evidence is insufficient, say that clearly.

Question ID: {id}
Category: {category}
Question: {question}
"""


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_env(model_name: str) -> dict:
    """Per-model environment for the claude subprocess.

    The proxy only serves the eval models, so we also point Claude Code's
    background ("haiku"/"sonnet"/"opus") model slots at the same model to avoid
    400s on the auxiliary calls it makes.
    """
    env = os.environ.copy()
    env["ANTHROPIC_MODEL"] = model_name
    env["ANTHROPIC_SMALL_FAST_MODEL"] = model_name
    env["ANTHROPIC_DEFAULT_HAIKU_MODEL"] = model_name
    env["ANTHROPIC_DEFAULT_SONNET_MODEL"] = model_name
    env["ANTHROPIC_DEFAULT_OPUS_MODEL"] = model_name
    # Keep the eval offline/quiet and avoid auto-update churn mid-run.
    env.setdefault("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")
    env.setdefault("DISABLE_TELEMETRY", "1")
    env.setdefault("DISABLE_ERROR_REPORTING", "1")
    env.setdefault("DISABLE_AUTOUPDATER", "1")
    return env


def run_one(model_name: str, prompt: str, args, env: dict):
    # --allowedTools is variadic; pass each tool as its own token.
    tool_tokens = [t.strip() for t in args.allowed_tools.split(",") if t.strip()]
    # The prompt is fed via stdin rather than as a trailing positional: both
    # --allowedTools and --add-dir take variadic values (<tools...>/<directories...>),
    # so a positional prompt placed after them gets swallowed as an extra value,
    # leaving claude --print with no input ("Input must be provided either through
    # stdin or as a prompt argument when using --print").
    cmd = [
        "claude",
        "-p",
        "--model", model_name,
        "--allowedTools", *tool_tokens,
        "--add-dir", str(REPO_ROOT / "data" / "raw" / "ippl"),
    ]
    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            text=True,
            input=prompt,
            capture_output=True,
            timeout=args.timeout,
            check=False,
            env=env,
        )
        answer = result.stdout.strip()
        error = "" if result.returncode == 0 else (result.stderr.strip() or f"exit {result.returncode}")
    except subprocess.TimeoutExpired:
        answer = ""
        error = f"timeout after {args.timeout}s"
    except Exception as exc:  # noqa: BLE001 - record any launcher failure
        answer = ""
        error = repr(exc)
    return answer, error, time.monotonic() - start


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", default=str(REPO_ROOT / "docs/evaluations/eval_questions_v2.json"))
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "docs/evaluations/answers"))
    parser.add_argument("--models", nargs="*", default=None,
                        help="Subset of labels to run (e.g. qwen25_7b_q4km gemma4_12b). Default: all.")
    parser.add_argument("--timeout", type=int, default=1800,
                        help="Per-question timeout in seconds.")
    parser.add_argument("--allowed-tools", default="Read,Grep,Glob",
                        help="Comma-separated tools Claude Code may use (read-only by default).")
    args = parser.parse_args()

    if shutil.which("claude") is None:
        print("ERROR: `claude` CLI not found on PATH. Install Claude Code first.", flush=True)
        return 1

    base_url = os.environ.get("ANTHROPIC_BASE_URL", "")
    if not base_url:
        print("WARNING: ANTHROPIC_BASE_URL is not set. Claude Code will hit the real "
              "Anthropic API, not your LiteLLM proxy. Run via run_eval_ssh.sh or export it.",
              flush=True)

    questions_path = Path(args.questions)
    questions = json.loads(questions_path.read_text())["questions"]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected = DEFAULT_MODELS
    if args.models:
        wanted = set(args.models)
        selected = [m for m in DEFAULT_MODELS if m[1] in wanted]
        if not selected:
            print(f"ERROR: none of {sorted(wanted)} match known labels "
                  f"{[m[1] for m in DEFAULT_MODELS]}.", flush=True)
            return 1

    for model_name, label, ollama_tag in selected:
        timestamp = now_stamp()
        out_path = out_dir / f"claude_code_{label}_{timestamp}.json"
        env = build_env(model_name)
        answers = []
        failures = 0
        started_at = now_iso()
        print(f"\n=== Running {model_name} ({len(questions)} questions) -> {out_path.name} ===",
              flush=True)

        def snapshot(complete: bool):
            payload = {
                "schema": "claude-code-model-matrix/v1",
                "model": model_name,
                "label": label,
                "run_complete": complete,
                "run_metadata": {
                    "run_label": label,
                    "claude_model": model_name,
                    "ollama_tag": ollama_tag,
                    "run_started_at_utc": started_at,
                    "run_finished_at_utc": now_iso() if complete else None,
                    "hostname": platform.node(),
                    "anthropic_base_url": base_url,
                    "questions_source": str(questions_path),
                    "questions_version": "v2",
                    "per_question_timeout_seconds": args.timeout,
                    "allowed_tools": args.allowed_tools,
                    "answer_count": len(answers),
                    "failure_count": failures,
                },
                "questions_source": str(questions_path),
                "answers": answers,
            }
            out_path.write_text(json.dumps(payload, indent=2))

        for i, q in enumerate(questions, 1):
            prompt = PROMPT_TEMPLATE.format(id=q["id"], category=q["category"], question=q["question"])
            print(f"[{i}/{len(questions)}] {model_name} {q['id']}: {q['question']}", flush=True)
            answer, error, latency = run_one(model_name, prompt, args, env)
            if error or not answer:
                failures += 1
            answers.append({
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "answer": answer,
                "error": error,
                "latency_seconds": latency,
            })
            snapshot(complete=False)  # incremental save so a crash keeps progress

        snapshot(complete=True)
        print(f"Wrote {len(answers)} answers ({failures} failures) to {out_path}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
