import json
import multiprocessing
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
import requests
from fastapi.testclient import TestClient


NOON = datetime.fromisoformat("2026-11-21T12:00:00+05:30")
ROW = {"customer_id": "ledger-A", "name": "Fixture", "phone_number": "9000000001",
       "due_date": "2026-11-20", "outstanding_amount": 125}
TRIGGER = "ledger-A-2026-11-20-2026-11-21"
RELAY = "https://sandbox.cashfree.com/relay/inbound/webhook/fixture"


def response(code):
    result = requests.Response()
    result.status_code = code
    result._content = b""
    return result


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setenv("COLLECTIONS_DB", str(tmp_path / "collections.sqlite3"))
    monkeypatch.setenv("TRIGGER_API_KEY", "test-trigger-key")
    monkeypatch.setenv("CALL_API_TOKEN", "")
    import trigger_api as t

    monkeypatch.setattr(t, "CALL_API_URL", "https://caller.invalid/fixture")
    monkeypatch.setattr(t, "CALL_API_TOKEN", None)
    monkeypatch.setattr(t, "now_ist", lambda: NOON)
    monkeypatch.setattr(requests.Session, "send", lambda *a, **kw: pytest.fail("unexpected network access"))
    return t


def worker(output, route, gate=None, crash=False):
    """Fresh server process, same database, fake Relay; all network access is disabled."""
    import trigger_api as t

    t.now_ist = lambda: NOON
    t.CALL_API_URL = RELAY
    t.read_notebook = lambda *args: [ROW]
    if gate is not None:
        translate = t.relay_call_payload

        def rendezvous(payload):
            gate.wait(timeout=15)  # Both routes already passed the eligibility check.
            return translate(payload)

        t.relay_call_payload = rendezvous

    def post(url, *, json, **kw):
        with output.with_suffix(".posts").open("a") as calls:
            calls.write(json["data"]["request_id"] + "\n")
        if crash:
            os._exit(23)  # The remote received the POST; no local cleanup can run.
        return response(200)

    requests.Session.send = Mock(side_effect=AssertionError("unexpected network access"))
    requests.post = post
    with TestClient(t.app, headers={"X-API-Key": "test-trigger-key"}) as client:
        if route == "call":
            result = client.post("/trigger/call", json=ROW).json()
        else:
            result = client.post("/trigger/notebook", files={"file": ("fixture.png", b"mock OCR")}).json()["results"][0]
    output.write_text(json.dumps(result))


def test_parallel_typed_and_notebook_workers_share_one_post_even_after_restart(api, tmp_path):
    ctx = multiprocessing.get_context("spawn")
    gate = ctx.Barrier(2)
    paths = [tmp_path / route for route in ("call", "notebook")]
    workers = [ctx.Process(target=worker, args=(path, path.name, gate)) for path in paths]
    for process in workers:
        process.start()
    try:
        for process in workers:
            process.join(25)
            assert process.exitcode == 0
    finally:
        for process in workers:
            if process.is_alive():
                process.kill()
                process.join()
    posts = [line for path in tmp_path.glob("*.posts") for line in path.read_text().splitlines()]
    assert posts == [TRIGGER]
    results = [json.loads(path.read_text()) for path in paths]
    assert sorted(row["status"] for row in results) == ["call_triggered", "skipped"]
    assert next(row for row in results if row["status"] == "call_triggered")["dispatch_state"] == "queued"

    # Neither sending process is running anymore. This interpreter has never sent a call.
    replay = api.check_and_call(ROW, dry_run=False)
    assert (replay["status"], replay["dispatch_state"], replay["trigger_id"]) == ("skipped", "queued", TRIGGER)
    assert not api.lender_queue()["call_queue"]


def test_worker_death_after_send_is_visible_and_cannot_redial(api, tmp_path):
    output = tmp_path / "crashed"
    process = multiprocessing.get_context("spawn").Process(target=worker, args=(output, "call", None, True))
    process.start()
    process.join(25)
    if process.is_alive():
        process.kill()
        process.join()
    assert process.exitcode == 23 and output.with_suffix(".posts").read_text().splitlines() == [TRIGGER]
    saved, = api.lender_queue()["other"]
    assert saved["dispatch_state"] == "unknown"
    assert TRIGGER in saved["reason"] and "logs" in saved["reason"].lower()
    assert api.check_and_call(ROW, dry_run=False)["dispatch_state"] == "unknown"


def test_preview_and_missing_endpoint_leave_daily_slot_free_and_next_ist_day_reopens(api, monkeypatch):
    post = Mock(side_effect=[response(201), response(202)])
    monkeypatch.setattr(requests, "post", post)
    with monkeypatch.context() as m:
        m.setattr(api, "CALL_API_URL", None)
        assert api.check_and_call(ROW, dry_run=False)["status"] == "call_api_not_set"
    assert api.check_and_call(ROW, dry_run=True)["status"] == "would_call"
    assert len(api.lender_queue()["call_queue"]) == 1
    post.assert_not_called()
    with closing(sqlite3.connect(os.environ["COLLECTIONS_DB"])) as db:
        assert db.execute("SELECT COUNT(*) FROM dispatch_ledger").fetchone() == (0,)
    first = api.check_and_call(ROW, dry_run=False)
    assert (first["status"], first["dispatch_state"]) == ("call_triggered", "accepted")
    assert first["reason"] == post.call_args.kwargs["json"]["reason"]
    assert api.check_and_call(ROW, dry_run=True)["dispatch_state"] == "accepted"
    tomorrow = NOON + timedelta(days=1)
    assert api.check_and_call(ROW, dry_run=False, now=tomorrow.replace(hour=0))["status"] == "blocked"
    result = api.check_and_call(ROW, dry_run=False, now=tomorrow.replace(hour=8).astimezone(timezone.utc))
    assert (result["status"], result["dispatch_state"]) == ("call_triggered", "queued")
    assert [call.kwargs["json"]["trigger_id"] for call in post.call_args_list] == [TRIGGER, "ledger-A-2026-11-20-2026-11-22"]


@pytest.mark.parametrize('change,want', [('full', 'paid'), ('partial','needs_check'), ('stop','no_contact'),
                                         ('claim','payment_hold'), ('promise','promise_wait')])
def test_committed_change_during_call_preparation_wins_before_taking_the_daily_slot(api, monkeypatch, change, want):
    monkeypatch.setattr(api, 'CALL_API_URL', RELAY)
    original = api.relay_call_payload

    def update_while_preparing(payload):
        iid = payload['installment_id']
        if change in ('full', 'partial'):
            api.store.record_payment(iid, 12500 if change == 'full' else 5000)
        elif change == 'claim':
            api.store.mark_claim(iid)
        elif change == 'stop':
            api.contact_preferences.record(ROW['phone_number'], 'no_contact')
        else:
            request = api.promises.PromiseRequest(amount=10,promise_at=(NOON+timedelta(hours=2)).isoformat())
            api.promises.record_promise(iid, request, NOON)
        return original(payload)

    monkeypatch.setattr(api, 'relay_call_payload', update_while_preparing)
    sent = Mock(return_value=response(202))
    monkeypatch.setattr(api.requests, 'post', sent)
    result = api.check_and_call(ROW, False)
    assert result['status'] == want
    assert sent.call_count == 0
    assert api.dispatch_ledger.states_for_day(NOON.date().isoformat()) == {}


@pytest.mark.parametrize("outcome", [requests.ReadTimeout(), requests.ConnectionError(), 307, 409, 503])
def test_uncertain_outcome_blocks_another_post_and_tells_operator_what_to_check(api, monkeypatch, outcome):
    post = Mock(side_effect=[response(outcome) if isinstance(outcome, int) else outcome])
    monkeypatch.setattr(requests, "post", post)
    first = api.check_and_call(ROW, dry_run=False)
    replay = api.check_and_call(ROW, dry_run=False)
    assert first["status"] == "call_api_error" and replay["status"] == "skipped"
    for row in (first, replay, api.lender_queue()["other"][0]):
        assert row["dispatch_state"] == "unknown"
        assert TRIGGER in row["reason"] and "logs" in row["reason"].lower()
    assert post.call_count == 1 and post.call_args.kwargs["allow_redirects"] is False


def test_unknown_remains_visible_after_contact_hours_without_overriding_the_hold(api, monkeypatch):
    monkeypatch.setattr(requests, "post", Mock(side_effect=requests.ReadTimeout()))
    api.check_and_call(ROW, dry_run=False)
    monkeypatch.setattr(api, "now_ist", lambda: NOON.replace(hour=20))
    held, = api.lender_queue()["other"]
    assert held["status"] == "blocked" and held["dispatch_state"] == "unknown"
    assert TRIGGER in held["reason"] and "logs" in held["reason"].lower()


def test_provider_ack_with_local_write_failure_still_reports_ack_and_blocks_replays(api, monkeypatch):
    def accepted(*args, **kwargs):
        with closing(sqlite3.connect(os.environ["COLLECTIONS_DB"])) as db, db:
            db.execute("""CREATE TRIGGER fail_ack BEFORE UPDATE ON dispatch_ledger
                          BEGIN SELECT RAISE(ABORT, 'simulated write failure'); END""")
        return response(201)

    post = Mock(side_effect=accepted)
    monkeypatch.setattr(requests, "post", post)
    result = api.check_and_call(ROW, dry_run=False)
    assert (result["status"], result["dispatch_state"]) == ("call_triggered", "accepted")
    assert TRIGGER in result["next_step"] and "logs" in result["next_step"].lower()
    assert api.check_and_call(ROW, dry_run=False)["dispatch_state"] == "unknown"
    assert post.call_count == 1


def test_distinct_installments_of_one_borrower_do_not_consume_each_others_slot(api, monkeypatch):
    post = Mock(return_value=response(200))
    monkeypatch.setattr(requests, "post", post)
    for due in ("2026-11-20", "2026-11-21"):
        row = {**ROW, "due_date": due}
        assert api.check_and_call(row, dry_run=False)["status"] == "call_triggered"
        assert api.check_and_call(row, dry_run=False)["status"] == "skipped"
    assert post.call_count == 2


@pytest.mark.parametrize("rejection", [requests.ConnectTimeout(), 401, 422])
def test_definite_nonacceptance_allows_a_corrected_retry(api, monkeypatch, rejection):
    post = Mock(side_effect=[response(rejection) if isinstance(rejection, int) else rejection, response(200)])
    monkeypatch.setattr(requests, "post", post)
    assert api.check_and_call(ROW, dry_run=False)["status"] == "call_api_error"
    assert api.check_and_call(ROW, dry_run=False)["dispatch_state"] == "accepted"
    assert post.call_count == 2
