"""Evaluate a classifier on the labelled demo emails.

Usage: python -m job_agent.evaluate [--baseline] [--delay SECONDS] [--out docs/eval.md]
"""

from __future__ import annotations

import argparse
import time
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from job_agent.classifier import Classifier, KeywordClassifier, LlmClassifier
from job_agent.demo_data import load_labelled_emails
from job_agent.models import Category, Extraction, LabelledEmail


def _norm(text: str | None) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).casefold().strip()


def text_matches(expected: str | None, got: str | None) -> bool:
    """None must match None; otherwise accept equality or containment after normalising."""
    e, g = _norm(expected), _norm(got)
    if not e or not g:
        return e == g
    return e == g or e in g or g in e


@dataclass
class Report:
    n: int = 0
    category_ok: int = 0
    company_ok: int = 0
    role_ok: int = 0
    due_ok: int = 0
    per_category: dict[Category, list[int]] = field(
        default_factory=lambda: defaultdict(lambda: [0, 0])
    )
    errors: list[str] = field(default_factory=list)


def score(items: list[LabelledEmail], predictions: list[Extraction]) -> Report:
    r = Report()
    for item, pred in zip(items, predictions, strict=True):
        exp = item.expected
        r.n += 1
        hit = pred.category is exp.category
        r.category_ok += hit
        r.per_category[exp.category][0] += hit
        r.per_category[exp.category][1] += 1
        r.company_ok += text_matches(exp.company, pred.company)
        r.role_ok += text_matches(exp.role, pred.role)
        r.due_ok += pred.due == exp.due
        if not hit:
            r.errors.append(
                f"{item.email.id}: expected {exp.category.value}, got {pred.category.value}"
            )
    return r


def run(classifier: Classifier, items: list[LabelledEmail], delay: float = 0.0) -> list[Extraction]:
    out = []
    for i, item in enumerate(items):
        out.append(classifier.classify(item.email))
        if delay and i < len(items) - 1:
            time.sleep(delay)
    return out


def to_markdown(name: str, r: Report) -> str:
    pct = lambda ok, n: f"{100 * ok / n:.0f}% ({ok}/{n})"  # noqa: E731
    lines = [
        f"### {name}",
        "",
        "| Metric | Score |",
        "|---|---|",
        f"| Category | {pct(r.category_ok, r.n)} |",
        f"| Company | {pct(r.company_ok, r.n)} |",
        f"| Role | {pct(r.role_ok, r.n)} |",
        f"| Due date | {pct(r.due_ok, r.n)} |",
        "",
        "| Category | Accuracy |",
        "|---|---|",
    ]
    for cat in Category:
        ok, n = r.per_category[cat]
        lines.append(f"| {cat.value} | {pct(ok, n)} |")
    if r.errors:
        lines += ["", "Misclassified:", *[f"- {e}" for e in r.errors]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", action="store_true", help="also run the keyword baseline")
    parser.add_argument("--delay", type=float, default=4.0, help="seconds between LLM calls")
    parser.add_argument("--out", type=Path, default=None, help="write the report to this file")
    args = parser.parse_args()

    from job_agent.llm import get_llm_chain

    items = load_labelled_emails()
    sections = []
    if args.baseline:
        base = score(items, run(KeywordClassifier(), items))
        sections.append(to_markdown("Keyword baseline (category only)", base))
    llm_report = score(items, run(LlmClassifier(get_llm_chain()), items, args.delay))
    sections.append(to_markdown("LLM classifier (Gemini, structured output)", llm_report))
    text = "\n".join(sections)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text("# Evaluation\n\n" + text, encoding="utf-8")


if __name__ == "__main__":
    main()
