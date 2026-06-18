import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

questions_path = Path("docs/evaluations/eval_questions_v2.json")
out_path = Path("docs/evaluations/answers/claude_code_qwen25_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
out_path.parent.mkdir(parents=True, exist_ok=True)

questions = json.loads(questions_path.read_text())["questions"]
answers = []

for i, q in enumerate(questions, 1):
    prompt = f"""You are answering an IPPL benchmark question.

Use only repository files under data/raw/ippl and repository documentation.
Ground the answer in concrete files/symbols when possible.
If the repository evidence is insufficient, say that clearly.

Question ID: {q["id"]}
Category: {q["category"]}
Question: {q["question"]}
"""
    print(f"[{i}/{len(questions)}] {q['id']}: {q['question']}", flush=True)
    start = time.monotonic()
    try:
        result = subprocess.run(
            ["claude", "-p", "--model", "claude-qwen25", "--max-turns", "8", prompt],
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
        "schema": "claude-code-benchmark/v1",
        "model": "claude-qwen25",
        "questions_source": str(questions_path),
        "answers": answers,
    }, indent=2))

print(f"Wrote {len(answers)} answers to {out_path}")
