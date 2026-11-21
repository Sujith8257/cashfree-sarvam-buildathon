import json
import os

import pytest
import requests
from fastapi.testclient import TestClient

os.environ.setdefault("TRIGGER_API_KEY", "test-trigger-key")
import trigger_api as api


PAGE = b"%PDF-1.4\nsynthetic fixture"
HEADERS = {"X-API-Key": "test-trigger-key"}


def reply(data, status=200):
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(data).encode()
    return response


@pytest.fixture
def intake(monkeypatch, tmp_path):
    pending = []
    def route(_, request, **kwargs):
        assert request.url.startswith("https://api.sarvam.ai/doc-ai/v1/job/"), "Unexpected outbound dispatch"
        item = pending.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(requests.Session, "send", route)
    monkeypatch.setattr(api, "TRIGGER_KEY", "test-trigger-key")
    monkeypatch.setattr(api, "SARVAM_KEY", "ocr-fixture")
    monkeypatch.setenv("COLLECTIONS_DB", str(tmp_path / "test.sqlite3"))
    client = TestClient(api.app, raise_server_exceptions=False)
    def upload(page=PAGE, filename="page.pdf", mime="application/pdf"):
        return client.post("/trigger/notebook", headers=HEADERS, files={"file": (filename, page, mime)},
                           data={"dry_run": "false"})
    return pending, upload, client


def test_incomplete_work_never_registers_or_calls_borrowers(intake):
    replies, upload, client = intake
    replies.extend([reply({"job_id": "sample-1"}), reply({"status": "partially_completed"})])
    result = upload()
    assert result.status_code == 422
    assert "page" in result.json()["detail"].lower()
    assert client.get("/queue", headers=HEADERS).json()["other"] == []


@pytest.mark.parametrize("last,expected", [
    (requests.Timeout("synthetic private upstream detail"), 504),
    (reply({"message": "synthetic private upstream detail"}, 429), 503),
    (reply({"status": "not-an-extract-job-state"}), 502),
])
def test_provider_failure_is_actionable_without_echoing_response(intake, last, expected):
    replies, upload, _ = intake
    replies.extend([reply({"job_id": "sample-1"}), last])
    result = upload()
    assert result.status_code == expected
    assert "synthetic private upstream detail" not in result.text
    assert result.json()["detail"]


def test_rejects_the_entire_malformed_result_before_any_row_is_used(intake):
    replies, upload, client = intake
    replies.extend([reply({"job_id": "sample-1"}), reply({"status": "completed"}),
                    reply({"result": {"borrowers": [{"name": "fixture", "customer_id": "fixture", "phone_number": "9000000000",
                                                   "due_date": "2000-01-01", "outstanding_amount": 100}, "broken row"]}})])
    result = upload()
    assert result.status_code == 502
    state = client.get("/queue", headers=HEADERS).json()
    assert not state["other"] and not state["call_queue"]


@pytest.mark.parametrize("data,name,mime,expected", [
    (b"", "page.pdf", "application/pdf", 422), (b"plain text", "page.txt", "text/plain", 415),
    (b"x" * 17, "page.png", "image/png", 413),
])
def test_unusable_upload_is_rejected_before_ocr(intake, monkeypatch, data, name, mime, expected):
    monkeypatch.setattr(api, "MAX_NOTEBOOK_BYTES", 16, raising=False)
    _, upload, _ = intake
    assert upload(data, name, mime).status_code == expected


def test_valid_completed_empty_notebook_returns_zero_rows(intake):
    replies, upload, _ = intake
    replies.extend([reply({"job_id": "sample-1"}), reply({"status": "completed"}), reply({"result": {"borrowers": []}})])
    assert upload().json() == {"rows_read": 0, "calls": 0, "results": [], "extracted": []}
