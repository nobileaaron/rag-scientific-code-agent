import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

QUESTIONS_PATH = Path("docs/evaluations/eval_questions_v2.json")

MODELS = [
    ("claude-qwen25-7b-q4km", "qwen25_7b_q4km"),
    ("claude-qwen25-32b-q4km", "qwen25_32b_q4km"),
    ("claude-qwen35-9b", "qwen35_9b"),
    ("claude-gemma4-12b", "gemma4_12b"),
]

questions = json.loads(QUESTIONS_PATH.read_text())["questions"]
out_dir = Path("docs/evaluations/answers")
out_dir.mkdir(parents=True, exist_ok=True)

for model_name, label in MODELS:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"claude_code_{label}_{timestamp}.json"
    answers = []

    print(f"\n=== Running {model_name} ===", flush=True)

    for i, q in enumerate(questions, 1):
        prompt = f"""You are answering an IPPL benchmark question.

Use only repository files under data/raw/ippl and repository documentation.
Ground the answer in concrete files/symbols when possible.
If evidence is insufficient, say that clearly.

Question ID: {q["id"]}
Category: {q["category"]}
Question: {q["question"]}
"""

        print(f"[{i}/{len(questions)}] {model_name} {q['id']}", flush=True)
        start = time.monotonic()

        try:
            result = subprocess.run(
                ["claude", "-p", "--model", model_name, "--max-turns", "8", prompt],
                text=True,
                capture_output=True,
                timeout=1800,
                check=False,
            )
            answer = result.stdout.strip()
            error = None if result.returncode == 0 else result.stderr.strip()
        except Exception as exc:
            answer = ""
            error = repr(exc)

        answers.append({
            "id": q["id"],
            "category": q["category"],
            "question": q["question"],
            "answer": answer,
            "error": error,
            "latency_seconds": time.monotonic() - start,
        })

        out_path.write_text(json.dumps({
            "schema": "claude-code-model-matrix/v1",
            "model": model_name,
            "label": label,
            "questions_source": str(QUESTIONS_PATH),
            "run_complete": False,
            "answers": answers,
        }, indent=2))

    out_path.write_text(json.dumps({
        "schema": "claude-code-model-matrix/v1",
        "model": model_name,
        "label": label,
        "questions_source": str(QUESTIONS_PATH),
        "run_complete": True,
        "answers": answers,
    }, indent=2))

    print(f"Wrote {len(answers)} answers to {out_path}", flush=True)
