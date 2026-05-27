#!/usr/bin/env python3
"""Generate a comparison report between evaluation round 1 and round 2."""

from __future__ import annotations

import json
import re
import textwrap
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

V1_REPORT = REPO_ROOT / "docs" / "evaluations" / "codex_vs_local_llm_evaluation_20260423.md"
V2_REPORT = REPO_ROOT / "docs" / "evaluations" / "codex_vs_local_llm_evaluation_v2_20260424.md"
V1_QUESTIONS = REPO_ROOT / "docs" / "evaluations" / "eval_questions_v1.json"
V2_QUESTIONS = REPO_ROOT / "docs" / "evaluations" / "eval_questions_v2.json"
V1_ANSWERS = REPO_ROOT / "docs" / "evaluations" / "answers" / "eval_20260423T141904Z.json"
V2_ANSWERS = REPO_ROOT / "docs" / "evaluations" / "answers" / "eval_v2_20260424T140027Z.json"

OUTPUT_MD = REPO_ROOT / "docs" / "evaluations" / "evaluation_round1_vs_round2_20260424.md"
OUTPUT_PDF = REPO_ROOT / "docs" / "evaluations" / "evaluation_round1_vs_round2_20260424.pdf"


COMMIT_SUMMARY = [
    (
        "0db9dba",
        "Created `eval_job.sh` so the evaluation can run non-interactively on gwendolen and write answer files under `docs/evaluations/answers`.",
    ),
    (
        "31a61e5",
        "Improved lifecycle/location retrieval by detecting location intent, synthesizing exact API-bearing terms such as `Kokkos::initialize`, injecting literal matches, and boosting those exact call sites in reranking.",
    ),
    (
        "cb0b888",
        "Added comparison-aware retrieval for Poisson-solver tradeoff questions so the system retrieves both sides of the comparison instead of collapsing onto generic FFT infrastructure.",
    ),
    (
        "5511d34",
        "Created the V2 evaluation question set and updated `eval_job.sh` so SSH runs use the filtered V2 questions and write V2-labelled answer files.",
    ),
    (
        "2e51a05",
        "Shortened the content of supplementary symbol-entity chunks sent to the answering LLM so secondary context acts like support evidence rather than noisy full chunks.",
    ),
    (
        "c07cd94",
        "Added an eval-job-specific answer-model override mechanism so the cluster evaluation can use a different answer model without changing the normal local runtime settings.",
    ),
]

AVG_SCORE_KEY = "Average score (`Correct=1`, `Partial=0.5`, `Incorrect=0`)"


TOPIC_SUMMARY = [
    (
        "Location and lifecycle questions",
        "We worked on failures like “Where is Kokkos initialized and finalized inside IPPL?” and related exact-location questions. The main change was to stop relying purely on semantic similarity and instead rescue exact API call sites directly.",
    ),
    (
        "Algorithm-specific solver questions",
        "We focused on questions like the FFT-based periodic/open-boundary Poisson solver prompts, where retrieval was drifting into generic FFT infrastructure instead of solver implementations.",
    ),
    (
        "Data-flow questions",
        "We spent time on grid-to-particle and particle-to-grid handoff questions. The main theme was that these require cross-module evidence rather than more chunks from a single solver file.",
    ),
    (
        "Comparison questions",
        "We worked specifically on the FFT-vs-CG Poisson comparison case to make retrieval cover both solver families instead of flooding the prompt with FFT-only material.",
    ),
    (
        "Prompt hygiene for supplementary context",
        "We tightened how supplementary symbol-level chunks are rendered so they contribute only the most relevant support facts and a small code snippet, rather than a full second explanation block.",
    ),
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_overall_metrics(path: Path):
    text = path.read_text(encoding="utf-8")
    metrics = {}
    for line in text.splitlines():
        match = re.match(r"\| ([^|]+) \| ([^|]+) \|", line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key in {
            "Questions",
            "Correct",
            "Partial",
            "Incorrect",
            "Average score (`Correct=1`, `Partial=0.5`, `Incorrect=0`)",
        }:
            metrics[key] = value
    return metrics


def parse_category_table(path: Path):
    text = path.read_text(encoding="utf-8")
    start = text.index("## Category Breakdown")
    end = text.index("## Detailed Per-Question Evaluation")
    section = text[start:end]
    rows = []
    for line in section.splitlines():
        if not line.startswith("| "):
            continue
        parts = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(parts) != 6:
            continue
        if parts[0] == "Category" or parts[0].startswith("---"):
            continue
        rows.append(
            {
                "category": parts[0],
                "questions": int(parts[1]),
                "correct": int(parts[2]),
                "partial": int(parts[3]),
                "incorrect": int(parts[4]),
                "avg_score": float(parts[5]),
            }
        )
    return rows


def extract_question_set_changes():
    v1_questions = load_json(V1_QUESTIONS)["questions"]
    v2_questions = load_json(V2_QUESTIONS)["questions"]
    v2_ids = {question["id"] for question in v2_questions}
    removed = [question for question in v1_questions if question["id"] not in v2_ids]
    removed_by_category = Counter(question["category"] for question in removed)
    return removed, removed_by_category


def build_markdown():
    v1_metrics = parse_overall_metrics(V1_REPORT)
    v2_metrics = parse_overall_metrics(V2_REPORT)
    v1_categories = parse_category_table(V1_REPORT)
    v2_categories = parse_category_table(V2_REPORT)
    removed_questions, removed_by_category = extract_question_set_changes()
    v1_answers = load_json(V1_ANSWERS)
    v2_answers = load_json(V2_ANSWERS)

    lines = []
    lines.append("# Evaluation 1 vs Evaluation 2")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")
    lines.append("## Goal")
    lines.append("")
    lines.append(
        "This report compares the first and second evaluation rounds of the IPPL RAG system. "
        "The aim is to explain not only the score change, but also what changed in the question set "
        "and what retrieval/prompting work we did between the two runs."
    )
    lines.append("")
    lines.append("## Runs Compared")
    lines.append("")
    lines.append("| Run | Answer file | Question set | Host | Job id | Questions | Correct | Partial | Incorrect | Avg score |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|")
    lines.append(
        f"| Evaluation 1 | `docs/evaluations/answers/{V1_ANSWERS.name}` | "
        f"`docs/evaluations/{V1_QUESTIONS.name}` | `{v1_answers['run_metadata']['hostname']}` | "
        f"{v1_answers['run_metadata']['slurm_job_id']} | {v1_metrics['Questions']} | "
        f"{v1_metrics['Correct']} | {v1_metrics['Partial']} | {v1_metrics['Incorrect']} | "
        f"{float(v1_metrics[AVG_SCORE_KEY]):.3f} |"
    )
    lines.append(
        f"| Evaluation 2 | `docs/evaluations/answers/{V2_ANSWERS.name}` | "
        f"`docs/evaluations/{V2_QUESTIONS.name}` | `{v2_answers['run_metadata']['hostname']}` | "
        f"{v2_answers['run_metadata']['slurm_job_id']} | {v2_metrics['Questions']} | "
        f"{v2_metrics['Correct']} | {v2_metrics['Partial']} | {v2_metrics['Incorrect']} | "
        f"{float(v2_metrics[AVG_SCORE_KEY]):.3f} |"
    )
    lines.append("")
    lines.append("## High-Level Comparison")
    lines.append("")
    avg_delta = float(v2_metrics[AVG_SCORE_KEY]) - float(v1_metrics[AVG_SCORE_KEY])
    lines.append(
        f"- The average score increased from `{float(v1_metrics[AVG_SCORE_KEY]):.3f}` "
        f"to `{float(v2_metrics[AVG_SCORE_KEY]):.3f}` "
        f"(`+{avg_delta:.3f}`)."
    )
    lines.append(
        f"- The raw question count dropped from `{v1_metrics['Questions']}` to `{v2_metrics['Questions']}` because "
        "Evaluation 2 intentionally removed questions that depended on tests, mini-apps, and example source files."
    )
    lines.append(
        f"- Correct answers moved from `{v1_metrics['Correct']}` to `{v2_metrics['Correct']}`. That looks almost flat in "
        "absolute count, but the error count dropped substantially because the question set became more on-scope for the current retrieval setup."
    )
    lines.append(
        "- This is not a pure apples-to-apples benchmark because Evaluation 2 changed the question set. "
        "It is better read as: after focusing the benchmark on `src/` plus documentation, how well does the system now perform?"
    )
    lines.append("")
    lines.append("## What Changed in the Question Set")
    lines.append("")
    lines.append(
        f"Evaluation 2 removed `{len(removed_questions)}` questions from the original `{len(load_json(V1_QUESTIONS)['questions'])}`-question set."
    )
    lines.append("")
    lines.append("| Removed Category | Count |")
    lines.append("|---|---:|")
    for category, count in sorted(removed_by_category.items()):
        lines.append(f"| {category} | {count} |")
    lines.append("")
    lines.append("The removed questions were concentrated in the areas that were least aligned with the stated V2 scope:")
    lines.append("")
    for category in sorted(removed_by_category):
        lines.append(f"### Removed: {category}")
        lines.append("")
        for question in removed_questions:
            if question["category"] == category:
                lines.append(f"- `{question['id']}` — {question['question']}")
        lines.append("")
    lines.append(
        "The core idea of V2 was to keep only questions that should be answerable from IPPL `src/` code or "
        "repository documentation, and to drop questions whose best evidence lived in tests, mini-apps, or example files outside that scope."
    )
    lines.append("")
    lines.append("## What We Worked On Between the Two Evaluations")
    lines.append("")
    for title, description in TOPIC_SUMMARY:
        lines.append(f"### {title}")
        lines.append("")
        lines.append(description)
        lines.append("")
    lines.append("## Implementation Changes")
    lines.append("")
    lines.append("The most relevant changes between the two evaluations were:")
    lines.append("")
    for commit, summary in COMMIT_SUMMARY:
        lines.append(f"- `{commit}` — {summary}")
    lines.append("")
    lines.append("## Category-by-Category Comparison")
    lines.append("")
    v2_category_map = {row["category"]: row for row in v2_categories}
    lines.append("| Category | Eval 1 Avg | Eval 2 Avg | Notes |")
    lines.append("|---|---:|---:|---|")
    for row in v1_categories:
        category = row["category"]
        if category == "Examples And Miniapps":
            lines.append(f"| {category} | {row['avg_score']:.3f} | removed | Entire category removed in V2 because it depends on mini-app/example files outside the new scope. |")
            continue
        v2_row = v2_category_map.get(category)
        if not v2_row:
            lines.append(f"| {category} | {row['avg_score']:.3f} | removed | Category not present in V2. |")
            continue
        note = ""
        if category == "Definition Location":
            note = "Still weak; this is exactly where we focused the location/lifecycle retrieval work."
        elif category == "Algorithm":
            note = "Still mixed; algorithm questions remain sensitive to whether solver implementation files are surfaced."
        elif category == "Data Flow":
            note = "Still one of the weakest areas; cross-module handoff retrieval remains a hard problem."
        elif category == "Numerical Meaning":
            note = "Improved partly because V2 removed several mini-app-heavy numerical questions."
        elif category == "Build And Install":
            note = "Still weak even in V2; docs retrieval remains brittle here."
        elif category == "File Purpose":
            note = "Stable strength across both rounds."
        elif category == "Class Responsibility":
            note = "Stable strength across both rounds."
        else:
            note = "Broadly similar between the two rounds."
        lines.append(f"| {category} | {row['avg_score']:.3f} | {v2_row['avg_score']:.3f} | {note} |")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append(
        "Evaluation 2 is better than Evaluation 1 in one important sense: it measures the system on a question set that is more aligned with the intended retrieval scope. "
        "That makes the result easier to trust as a signal about the current code-and-doc RAG pipeline rather than as a mixture of code retrieval quality and off-scope example coverage."
    )
    lines.append("")
    lines.append(
        "At the same time, the comparison also shows that simply filtering the question set was not enough. "
        "The remaining weak areas are exactly the ones we investigated during development: precise implementation-location questions, algorithm questions that need the right solver file instead of a nearby helper, "
        "and data-flow questions that need evidence from more than one subsystem."
    )
    lines.append("")
    lines.append(
        "The strongest improvement in process quality is not a single score jump; it is that the work between the two runs made the benchmark more focused and made retrieval behavior more explicit and controllable. "
        "That gives a much better foundation for the next round of iteration."
    )
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append(
        "In short: Evaluation 2 is a cleaner benchmark, a slightly stronger result numerically, and a much better reflection of the retrieval work we actually did. "
        "The main development themes between the runs were narrowing the benchmark to `src/` plus docs, improving exact location retrieval, improving solver comparison retrieval, and reducing prompt noise from supplementary chunks."
    )
    lines.append("")
    return "\n".join(lines)


def markdown_to_plaintext(markdown_text: str) -> str:
    lines = []
    for raw in markdown_text.splitlines():
        line = raw
        if line.startswith("#"):
            line = line.lstrip("#").strip().upper()
        line = line.replace("**", "")
        line = line.replace("`", "")
        if line.startswith("|") and line.endswith("|"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            line = " | ".join(parts)
        lines.append(line)
    return "\n".join(lines)


class SimplePDF:
    def __init__(self, title: str):
        self.title = title
        self.pages: list[list[str]] = []

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def add_wrapped_text(self, text: str, width: int = 100, lines_per_page: int = 62) -> None:
        current: list[str] = []
        for raw in text.splitlines():
            if not raw.strip():
                wrapped = [""]
            else:
                wrapped = textwrap.wrap(
                    raw,
                    width=width,
                    break_long_words=False,
                    replace_whitespace=False,
                    drop_whitespace=False,
                )
            for line in wrapped:
                if len(current) >= lines_per_page:
                    self.pages.append(current)
                    current = []
                current.append(line)
        if current:
            self.pages.append(current)

    def write(self, path: Path) -> None:
        objects: list[bytes] = []

        def add_object(data: bytes) -> int:
            objects.append(data)
            return len(objects)

        font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")
        page_objs = []

        for page_index, page_lines in enumerate(self.pages, start=1):
            stream_lines = ["BT", "/F1 9 Tf", "50 800 Td", "11 TL"]
            header = f"{self.title}  |  page {page_index}/{len(self.pages)}"
            stream_lines.append(f"({self._escape(header)}) Tj")
            stream_lines.append("T*")
            stream_lines.append("T*")
            for line in page_lines:
                stream_lines.append(f"({self._escape(line)}) Tj")
                stream_lines.append("T*")
            stream_lines.append("ET")
            stream = "\n".join(stream_lines).encode("latin-1", "replace")
            content_obj = add_object(
                b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
            )
            page_objs.append(
                add_object(
                    (
                        f"<< /Type /Page /Parent 0 0 R /MediaBox [0 0 595 842] "
                        f"/Resources << /Font << /F1 {font_obj} 0 R >> >> "
                        f"/Contents {content_obj} 0 R >>"
                    ).encode("ascii")
                )
            )

        kids = " ".join(f"{obj} 0 R" for obj in page_objs)
        pages_obj = add_object(f"<< /Type /Pages /Kids [ {kids} ] /Count {len(page_objs)} >>".encode("ascii"))

        for objnum in page_objs:
            objects[objnum - 1] = objects[objnum - 1].replace(
                b"/Parent 0 0 R", f"/Parent {pages_obj} 0 R".encode("ascii")
            )

        catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii"))

        output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = [0]
        for i, obj in enumerate(objects, start=1):
            offsets.append(len(output))
            output.extend(f"{i} 0 obj\n".encode("ascii"))
            output.extend(obj)
            output.extend(b"\nendobj\n")

        xref_offset = len(output)
        output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
        output.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            output.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        output.extend(
            (
                f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\n"
                f"startxref\n{xref_offset}\n%%EOF\n"
            ).encode("ascii")
        )
        path.write_bytes(output)


def main():
    markdown = build_markdown()
    OUTPUT_MD.write_text(markdown, encoding="utf-8")

    pdf = SimplePDF("Evaluation 1 vs Evaluation 2")
    pdf.add_wrapped_text(markdown_to_plaintext(markdown))
    pdf.write(OUTPUT_PDF)

    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
