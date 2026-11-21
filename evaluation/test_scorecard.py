import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import pytest

from evaluation import scorecard as s


ROOT = Path(__file__).resolve().parents[1]


def test_judge_command_reports_the_real_queues_mixed_result_and_tie_audit():
    run = subprocess.run([sys.executable, "-m", "evaluation.scorecard", "--k", "3", "--json"],
                         cwd=ROOT, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert (report["rows"], report["eligible"], report["effective_k"]) == (8, 6, 3)
    assert report["ranked"] == {"ids": ["L006", "L004", "L005"], "hits": 2,
                                "precision": 2 / 3, "confirmed_paise": 100000}
    assert report["loan_id"] == {"ids": ["L001", "L002", "L003"], "hits": 1,
                                 "precision": 1 / 3, "confirmed_paise": 120000}
    for variant in ("name", "language", "name+language"):
        assert report["swaps"][variant] == {"checked": 28, "eligible_ties": 1, "changed": []}


def test_frozen_queues_do_not_follow_relabelled_outcomes():
    book = s.fixture("book.json")
    at = datetime.fromisoformat(book["as_of"])
    orders = s.freeze_orders(s.preview(book["rows"], at))
    outcomes = s.fixture("withheld_outcomes.json")
    before = s.compare(orders, outcomes, at, 1)
    assert before["ranked"]["hits"] == 0 and before["loan_id"]["hits"] == 1
    alternate = deepcopy(outcomes)
    loans = alternate["loans"]
    loans["L001"], loans["L006"] = loans["L006"], loans["L001"]
    after = s.compare(orders, alternate, at, 1)
    assert after["ranked"]["hits"] == 1 and after["loan_id"]["hits"] == 0
    for method in ("ranked", "loan_id"):
        assert before[method]["ids"] == after[method]["ids"]


def test_preview_rejects_non_snapshot_fields_and_ambiguous_ids():
    book = s.fixture("book.json")
    at = datetime.fromisoformat(book["as_of"])
    row = book["rows"][0]
    with pytest.raises(ValueError, match="snapshot fields"):
        s.preview([{**row, "confirmed_paise_next_week": 4500}], at)
    with pytest.raises(ValueError, match="unique"):
        s.preview([row, row], at)


def test_oversized_and_empty_budgets_use_the_number_actually_selected():
    book = s.fixture("book.json")
    at = datetime.fromisoformat(book["as_of"])
    queue = s.preview(book["rows"], at)
    labels = s.fixture("withheld_outcomes.json")
    report = s.compare(s.freeze_orders(queue), labels, at, 99)
    assert (report["requested_k"], report["effective_k"]) == (99, 6)
    for method in ("ranked", "loan_id"):
        assert report[method]["hits"] == 3
        assert report[method]["precision"] == 0.5
        assert report[method]["confirmed_paise"] == 220000
    for queue_, k in ((queue, 0), ([], 3)):
        empty = s.compare(s.freeze_orders(queue_), labels, at, k)
        assert empty["ranked"] == empty["loan_id"] == {
            "ids": [], "hits": 0, "precision": None, "confirmed_paise": 0}
    with pytest.raises(ValueError, match="nonnegative"):
        s.compare(s.freeze_orders(queue), labels, at, -1)


def test_missing_followup_cannot_be_counted_as_nonpayment():
    book = s.fixture("book.json")
    at = datetime.fromisoformat(book["as_of"])
    labels = s.fixture("withheld_outcomes.json")
    with pytest.raises(ValueError, match="horizon"):
        s.compare(s.freeze_orders(["L001"]), {**labels, "observed_through": book["as_of"]}, at, 1)
    del labels["loans"]["L003"]
    with pytest.raises(ValueError, match="L003"):
        s.compare(s.freeze_orders(["L001", "L003"]), labels, at, 1)


def test_labels_are_not_even_opened_until_every_endpoint_replay_has_finished(monkeypatch):
    book = s.fixture("book.json")
    book["rows"] = book["rows"][:2]
    real_fixture, real_preview = s.fixture, s.preview
    labels_open = False

    def load(name):
        nonlocal labels_open
        if name == "book.json":
            return book
        labels_open = True
        return real_fixture(name)

    def record(rows, at):
        assert not labels_open, "The endpoint must never run after labels have been opened"
        return real_preview(rows, at)

    monkeypatch.setattr(s, "fixture", load)
    monkeypatch.setattr(s, "preview", record)
    assert s.evaluate(1)["ranked"]["ids"] == ["L006"]
    assert labels_open


def test_audit_detects_a_name_sensitive_tie_break_without_changing_eligibility(monkeypatch):
    book = s.fixture("book.json")
    rows, at = book["rows"][:2], datetime.fromisoformat(book["as_of"])
    real_preview = s.preview

    def name_tiebreak(rows, at):
        names = {r["customer_id"]: r["name"] for r in rows}
        return sorted(real_preview(rows, at), key=names.__getitem__)

    monkeypatch.setattr(s, "preview", name_tiebreak)
    audit = s.audit_swaps(rows, at, name_tiebreak(rows, at))
    assert len(audit["name"]["changed"]) == len(audit["name+language"]["changed"]) == 1
    assert audit["language"]["changed"] == []


def test_duplicate_ledger_events_cannot_inflate_confirmed_amounts():
    labels = s.fixture("withheld_outcomes.json")
    labels["loans"]["L004"].append(labels["loans"]["L004"][0])
    with pytest.raises(ValueError, match="duplicate"):
        s.compare(s.freeze_orders(["L004"]), labels, datetime.fromisoformat(s.fixture("book.json")["as_of"]), 1)
