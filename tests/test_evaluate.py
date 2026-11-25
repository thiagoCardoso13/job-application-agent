from job_agent.demo_data import load_labelled_emails
from job_agent.evaluate import score, text_matches, to_markdown


def test_text_matches_ignores_accents_case_and_containment():
    assert text_matches("Sol Mediterráneo", "sol mediterraneo")
    assert text_matches("Backend Developer (Python)", "Backend Developer")
    assert text_matches(None, None)
    assert not text_matches("Acme", None)
    assert not text_matches("Acme", "Globex")


def test_perfect_predictions_score_100():
    items = load_labelled_emails()
    report = score(items, [i.expected for i in items])
    assert report.category_ok == report.company_ok == report.role_ok == report.due_ok == 30
    assert not report.errors
    assert "100% (30/30)" in to_markdown("x", report)
