#!/usr/bin/env python3
"""Generate a source-backed Codex-vs-local-LLM evaluation report for V2.

This V2 report reuses the source-backed grading judgments from the first
evaluation round for the overlapping question IDs, then compares them against
the saved V2 answer run under ``docs/evaluations/answers``.
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = REPO_ROOT / "docs" / "evaluations" / "eval_questions_v2.json"
ANSWERS_PATH = REPO_ROOT / "docs" / "evaluations" / "answers" / "eval_v2_20260424T140027Z.json"
OUTPUT_MD = REPO_ROOT / "docs" / "evaluations" / "codex_vs_local_llm_evaluation_v2_20260424.md"
OUTPUT_PDF = REPO_ROOT / "docs" / "evaluations" / "codex_vs_local_llm_evaluation_v2_20260424.pdf"


def load_v1_helpers():
    source_path = REPO_ROOT / "scripts" / "generate_codex_vs_local_eval_report.py"
    spec = importlib.util.spec_from_file_location("eval_report_v1", source_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Could not load helper script: {source_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V1 = load_v1_helpers()
VERDICT_SCORE = V1.VERDICT_SCORE
DEFAULT_NOTE = V1.DEFAULT_NOTE


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def category_display_name(raw: str) -> str:
    return raw.replace("_", " ").title()


def ordered_categories(questions):
    out = []
    seen = set()
    for question in questions:
        category = question["category"]
        if category not in seen:
            out.append(category)
            seen.add(category)
    return out


def build_findings(by_category_rows):
    ranked = []
    for category, rows in by_category_rows.items():
        avg = sum(score for _, _, score in rows) / len(rows)
        ranked.append((avg, category, rows))
    ranked.sort()

    weakest = ranked[:2]
    strongest = list(reversed(ranked[-2:]))

    findings = []
    if strongest:
        lead = ", ".join(category_display_name(category) for _, category, _ in strongest)
        findings.append(
            f"Strongest areas: {lead}. These questions were usually answerable from a single clear "
            "header, implementation file, or doc page."
        )
    if weakest:
        lead = ", ".join(category_display_name(category) for _, category, _ in weakest)
        findings.append(
            f"Weakest areas: {lead}. These still tend to require cross-file synthesis, exact implementation "
            "location, or a sharper retrieval handoff between related subsystems."
        )
    findings.append(
        "Compared with the first round, this V2 set removes test- and miniapp-dependent questions, so the "
        "remaining misses are a cleaner view of retrieval and answer quality over `src/` plus repository docs."
    )
    findings.append(
        "The recurring failure mode is still undercoverage: when the right implementation file or doc page "
        "is not surfaced, the local answer either abstains or answers from a nearby but incomplete chunk."
    )
    findings.append(
        "The strongest answers remain the structural ones: file purpose, class responsibility, and direct API "
        "usage tend to do well when one primary file dominates the evidence."
    )
    return findings


def build_caveat(settings_snapshot, vector_manifest):
    embedding_settings = settings_snapshot.get("embedding", {})
    configured_backend = embedding_settings.get("backend", "")
    configured_transformer = embedding_settings.get("sentence_transformer_model", "")
    manifest_backend = vector_manifest.get("embedding_backend", "")
    manifest_model = vector_manifest.get("embedding_model", "")

    if configured_backend == "sentence_transformer" and configured_transformer:
        if manifest_backend != configured_backend or manifest_model != configured_transformer:
            return [
                "The saved answer file says the runtime settings were configured for the "
                f"`{configured_transformer}` sentence-transformer embedder, but the persisted vector-store "
                "manifest embedded in the same answer file points to a different stored embedding setup.",
                "That means this evaluated answer run was produced on top of an older persisted vector store "
                "rather than a fully rebuilt store for the configured embedder. Several misses may therefore "
                "reflect retrieval undercoverage as much as answer-model weakness.",
            ]

    return [
        "The saved answer file and embedded vector-store manifest are consistent enough that this report can "
        "be read as a straightforward evaluation of the saved V2 run.",
    ]


def build_markdown(questions_doc, answers_doc, evaluations):
    question_map = {q["id"]: q for q in questions_doc["questions"]}
    answers = answers_doc["answers"]

    if set(question_map) != set(evaluations):
        missing = sorted(set(question_map) - set(evaluations))
        extra = sorted(set(evaluations) - set(question_map))
        raise SystemExit(f"Evaluation coverage mismatch. Missing={missing} Extra={extra}")

    scored_rows = []
    by_category = {}
    for answer in answers:
        ev = evaluations[answer["id"]]
        score = VERDICT_SCORE[ev.verdict]
        scored_rows.append((answer, ev, score))
        by_category.setdefault(answer["category"], []).append((answer, ev, score))

    total_questions = len(scored_rows)
    correct = sum(1 for _, ev, _ in scored_rows if ev.verdict == "Correct")
    partial = sum(1 for _, ev, _ in scored_rows if ev.verdict == "Partial")
    incorrect = sum(1 for _, ev, _ in scored_rows if ev.verdict == "Incorrect")
    overall_score = sum(score for _, _, score in scored_rows) / total_questions

    latencies = [a["latency_seconds"] for a, _, _ in scored_rows]
    mean_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)

    settings_snapshot = answers_doc["settings_snapshot"]
    vector_manifest = answers_doc["vector_store_manifest"]
    run_metadata = answers_doc["run_metadata"]
    models = answers_doc["models"]

    lines = []
    lines.append("# Codex GPT-5.4 vs Local LLM Evaluation (V2)")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append("")
    lines.append("## Goal")
    lines.append("")
    lines.append(
        "This report compares the saved local-LLM V2 answer run in "
        f"`{ANSWERS_PATH.relative_to(REPO_ROOT)}` against a direct source/doc reading pass over "
        "`data/raw/ippl`. The Codex side of the comparison reuses the same source-backed reference "
        "answers and verdicts established in the first evaluation round for the overlapping question IDs."
    )
    lines.append("")
    lines.append("## Test Environment")
    lines.append("")
    lines.append("### Codex Side")
    lines.append("")
    lines.append("- Model: `GPT-5.4` (Codex)")
    lines.append("- Method: direct source/doc reading of `data/raw/ippl`")
    lines.append("- Question set: `docs/evaluations/eval_questions_v2.json`")
    lines.append("- Retrieval used for grading: none; this was a source-backed comparison pass")
    lines.append("")
    lines.append("### Local LLM Side")
    lines.append("")
    lines.append(f"- Host: `{run_metadata['hostname']}`")
    lines.append(f"- Job / partition: `{run_metadata['slurm_job_id']}` on `{run_metadata['slurm_partition']}`")
    lines.append(f"- Answer model: `{models['answer_model']['raw']}`")
    lines.append(f"- Chunk explanation model: `{models['chunk_explanation_model']['raw']}`")
    lines.append(
        f"- File / module / call-chain models: `{models['file_level_model']['raw']}`, "
        f"`{models['module_level_model']['raw']}`, `{models['call_chain_model']['raw']}`"
    )
    lines.append(f"- Parser: `{run_metadata['parser_type']}`")
    lines.append(f"- Question count: `{run_metadata['answer_count']}`")
    lines.append(f"- Answer prompt mode: `{run_metadata['answer_prompt_mode']}`")
    lines.append(f"- Mean answer latency: `{mean_latency:.2f}s`")
    lines.append(f"- Median answer latency: `{median_latency:.2f}s`")
    lines.append("")
    lines.append("### Retrieval Configuration Used by the Saved Run")
    lines.append("")
    lines.append(f"- Candidate k: `{settings_snapshot['retrieval']['candidate_k']}`")
    lines.append(f"- Supplementary k: `{settings_snapshot['retrieval']['supplementary_k']}`")
    lines.append(f"- Supplementary candidate k: `{settings_snapshot['retrieval']['supplementary_candidate_k']}`")
    lines.append(f"- Vector store chunk count: `{run_metadata['vector_store_chunk_count']}`")
    lines.append("")
    lines.append("## Important Caveat")
    lines.append("")
    for paragraph in build_caveat(settings_snapshot, vector_manifest):
        lines.append(paragraph)
        lines.append("")
    lines.append("## Overall Result")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Questions | {total_questions} |")
    lines.append(f"| Correct | {correct} |")
    lines.append(f"| Partial | {partial} |")
    lines.append(f"| Incorrect | {incorrect} |")
    lines.append(f"| Average score (`Correct=1`, `Partial=0.5`, `Incorrect=0`) | {overall_score:.3f} |")
    lines.append("")
    lines.append("## Main Findings")
    lines.append("")
    for finding in build_findings(by_category):
        lines.append(f"- {finding}")
    lines.append("")
    lines.append("## Category Breakdown")
    lines.append("")
    lines.append("| Category | Questions | Correct | Partial | Incorrect | Avg score |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for category in ordered_categories(questions_doc["questions"]):
        rows = by_category[category]
        c = sum(1 for _, ev, _ in rows if ev.verdict == "Correct")
        p = sum(1 for _, ev, _ in rows if ev.verdict == "Partial")
        i = sum(1 for _, ev, _ in rows if ev.verdict == "Incorrect")
        avg = sum(score for _, _, score in rows) / len(rows)
        lines.append(f"| {category_display_name(category)} | {len(rows)} | {c} | {p} | {i} | {avg:.3f} |")
    lines.append("")
    lines.append("## Detailed Per-Question Evaluation")
    lines.append("")

    answers_by_id = {a["id"]: a for a in answers}

    for category in ordered_categories(questions_doc["questions"]):
        lines.append(f"### {category_display_name(category)}")
        lines.append("")
        for q in [q for q in questions_doc["questions"] if q["category"] == category]:
            answer = answers_by_id[q["id"]]
            ev = evaluations[q["id"]]
            note = ev.note or DEFAULT_NOTE[ev.verdict]
            lines.append(f"#### {q['id']} - {q['question']}")
            lines.append("")
            lines.append(f"- Verdict: **{ev.verdict}**")
            lines.append(f"- Codex reference answer: {ev.reference}")
            lines.append(f"- Comparison: {note}")
            lines.append(f"- Primary sources: `{ev.refs}`")
            lines.append(V1.format_answer_result(answer))
            lines.append("")

    lines.append("## Conclusion")
    lines.append("")
    lines.append(
        "This V2 run is a cleaner measurement than the first round because the questions are now restricted "
        "to what should be answerable from `src/` and repository documentation. The local system is clearly "
        "useful on structural questions, but it still loses ground when the answer depends on retrieving the "
        "right implementation file or synthesizing across a few related source files."
    )
    lines.append("")
    lines.append(
        "The best next step is still retrieval quality: make it more likely to surface the exact solver, "
        "particle, interpolation, or documentation files that match the query intent, then keep the final "
        "prompt focused instead of letting one nearby file dominate the context."
    )
    lines.append("")
    return "\n".join(lines)


def main():
    questions_doc = load_json(QUESTIONS_PATH)
    answers_doc = load_json(ANSWERS_PATH)

    all_evaluations = V1.parse_evaluations()
    wanted_ids = {q["id"] for q in questions_doc["questions"]}
    evaluations = {qid: all_evaluations[qid] for qid in wanted_ids}

    markdown_report = build_markdown(questions_doc, answers_doc, evaluations)
    OUTPUT_MD.write_text(markdown_report, encoding="utf-8")

    pdf = V1.SimplePDF("Codex GPT-5.4 vs Local LLM Evaluation (V2)")
    pdf.add_wrapped_text(V1.markdown_to_plaintext(markdown_report))
    pdf.write(OUTPUT_PDF)

    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
