import base64
from datetime import date

from job_agent.sources import DemoSource, GmailSource, extract_body, parse_message


def b64(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def message(id_="m1", parts=None, body=None, ts="1762300800000"):  # 2025-11-05 00:00 UTC
    payload = {
        "headers": [
            {"name": "From", "value": "rec@acme.example"},
            {"name": "Subject", "value": "Interview"},
        ]
    }
    if parts is not None:
        payload["parts"] = parts
    if body is not None:
        payload["mimeType"] = "text/plain"
        payload["body"] = {"data": b64(body)}
    return {"id": id_, "internalDate": ts, "payload": payload}


def test_parse_plain_message():
    e = parse_message(message(body="Hello Thiago"))
    assert (e.id, e.sender, e.subject) == ("m1", "rec@acme.example", "Interview")
    assert e.body == "Hello Thiago"
    assert e.received == date(2025, 11, 5)


def test_prefers_plain_over_html_in_multipart():
    parts = [
        {"mimeType": "text/html", "body": {"data": b64("<p>HTML version</p>")}},
        {"mimeType": "text/plain", "body": {"data": b64("Plain version")}},
    ]
    assert extract_body({"parts": parts}) == "Plain version"


def test_html_only_is_stripped_and_unescaped():
    parts = [
        {
            "mimeType": "text/html",
            "body": {"data": b64("<style>x{}</style><p>Hi&nbsp;<b>there</b> &amp; welcome</p>")},
        }
    ]
    assert extract_body({"parts": parts}) == "Hi there & welcome"


def test_body_is_truncated():
    assert len(extract_body({"mimeType": "text/plain", "body": {"data": b64("a" * 9000)}})) == 4000


class FakeExec:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class FakeGmail:
    def __init__(self, msgs):
        self.msgs, self.calls = {m["id"]: m for m in msgs}, []

    def users(self):
        return self

    def messages(self):
        return self

    def list(self, **kw):
        self.calls.append(("list", kw))
        return FakeExec({"messages": [{"id": i} for i in self.msgs]})

    def get(self, **kw):
        self.calls.append(("get", kw))
        return FakeExec(self.msgs[kw["id"]])


def test_gmail_source_fetches_every_listed_message_read_only():
    svc = FakeGmail([message("a", body="one"), message("b", body="two")])
    emails = GmailSource(service=svc, query="newer_than:7d").fetch()
    assert [e.id for e in emails] == ["a", "b"]
    assert svc.calls[0][1]["q"] == "newer_than:7d"
    assert {name for name, _ in svc.calls} == {"list", "get"}  # nothing that writes


def test_demo_source_loads_30_emails():
    assert len(DemoSource().fetch()) == 30
