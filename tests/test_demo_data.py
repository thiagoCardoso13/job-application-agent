from collections import Counter

from job_agent.demo_data import load_labelled_emails
from job_agent.models import Category


def test_demo_set_is_valid_and_balanced():
    items = load_labelled_emails()
    assert len(items) == 30
    ids = [i.email.id for i in items]
    assert len(set(ids)) == len(ids)
    counts = Counter(i.expected.category for i in items)
    assert set(counts) == set(Category)
    assert {i.email.lang for i in items} == {"en", "es"}


def test_non_other_emails_have_company_and_role():
    for i in load_labelled_emails():
        if i.expected.category is not Category.OTHER:
            assert i.expected.company and i.expected.role, i.email.id
