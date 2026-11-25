"""Classify the demo emails once with the real model and save the answers.

The public demo replays these so visitors can run the whole agent without spending the free
Gemini quota. Run: PYTHONPATH=src python scripts/precompute.py
"""

import json
import time
from pathlib import Path

from job_agent.classifier import LlmClassifier
from job_agent.demo_data import load_emails
from job_agent.llm import get_llm_chain

OUT = Path(__file__).resolve().parents[1] / "demo_data" / "precomputed.json"


def main() -> None:
    clf = LlmClassifier(get_llm_chain())
    emails = load_emails()
    # Resumable: keep answers already saved, so a quota error only costs the missing ones.
    results = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    for i, email in enumerate(emails):
        if email.id in results:
            continue
        results[email.id] = json.loads(clf.classify(email).model_dump_json())
        OUT.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{i + 1}/{len(emails)} {email.id}")
        time.sleep(3)
    print(f"done: {len(results)}/{len(emails)} saved in {OUT}")


if __name__ == "__main__":
    main()
