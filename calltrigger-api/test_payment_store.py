import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from functools import partial
from importlib import import_module, reload
from pathlib import Path
from threading import Barrier

import pytest


PROFILE = {"customer_id": "", "name": "O'Neil", "phone_number": "9876543210", "due_date": "2026-11-20"}
CALLBACK = "2026-11-24T15:30:00+05:30"


@pytest.fixture(autouse=True)
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "collections.sqlite3"
    monkeypatch.setenv("COLLECTIONS_DB", str(path))
    return path


@pytest.fixture
def store(db_path):
    return import_module("payment_store")


def test_database_is_lazy_and_follows_current_env(db_path, tmp_path, monkeypatch):
    store = reload(import_module("payment_store"))
    assert not db_path.exists()
    store.register("first", PROFILE, 100)

    monkeypatch.setenv("COLLECTIONS_DB", str(tmp_path / "other.sqlite3"))
    assert store.get("first") is None
    monkeypatch.setenv("COLLECTIONS_DB", str(db_path))
    assert store.get("first")["amount_paise"] == 100


def test_register_returns_only_contract_fields_and_lists_in_insertion_order(store, db_path):
    extra = "not-for-storage@example.test"
    expected = {**PROFILE, "installment_id": "z'1", "link_id": "emi-z'1", "amount_paise": 12345,
                "paid_paise": 0, "claimed_paid": False, "callback_at": None}

    assert store.all_installments() == []
    first = store.register("z'1", {**PROFILE, "email": extra}, 12345)
    assert first == expected
    assert first["claimed_paid"] is False
    assert type(first["amount_paise"]) is int and type(first["paid_paise"]) is int
    second = store.register("a", PROFILE, 200)
    assert store.get("z'1") == expected
    assert store.all_installments() == [expected, second]
    with closing(sqlite3.connect(db_path)) as db:
        assert extra not in "\n".join(db.iterdump())


@pytest.mark.parametrize("amount", [0, -1, True, 12.5, "100", 2**63])
def test_new_amount_requires_positive_sqlite_integer(store, amount):
    with pytest.raises(ValueError):
        store.register("i", PROFILE, amount)
    assert store.get("i") is None


def test_largest_sqlite_amount_is_preserved_exactly(store):
    amount = 2**63 - 1
    assert store.register("i", PROFILE, amount)["amount_paise"] == amount
    assert store.record_payment("i", amount)["paid_paise"] == amount


@pytest.mark.parametrize("profile", [
    {**PROFILE, "phone_number": "+919876543210"}, {**PROFILE, "phone_number": "1234567890"},
    {**PROFILE, "phone_number": "९८७६५४३२१०"}, {**PROFILE, "due_date": "2026-02-30"},
    {**PROFILE, "due_date": "20/11/2026"}, {**PROFILE, "name": None},
    {k: v for k, v in PROFILE.items() if k != "customer_id"},
])
def test_invalid_profile_is_not_persisted(store, profile):
    with pytest.raises(ValueError):
        store.register("i", profile, 100)
    assert store.get("i") is None


def test_installment_id_must_be_nonempty_text(store):
    with pytest.raises(ValueError):
        store.register("", PROFILE, 100)
    assert store.all_installments() == []


def test_duplicate_and_out_of_order_cumulative_payments_do_not_reopen_debt(store):
    initial = store.register("i", PROFILE, 1237)
    for received, verified in [(0, 0), (337, 337), (337, 337), (12, 337), (1237, 1237), (0, 1237)]:
        assert store.record_payment("i", received) == {**initial, "paid_paise": verified}
    assert store.get("i")["paid_paise"] == 1237


@pytest.mark.parametrize("invalid", [-1, True, 1.5, "80", 101, 2**63])
def test_invalid_payment_leaves_verified_balance_untouched(store, invalid):
    store.register("i", PROFILE, 100)
    prior = store.record_payment("i", 40)
    with pytest.raises(ValueError):
        store.record_payment("i", invalid)
    assert store.get("i") == prior


def test_claim_and_reschedule_preserve_each_other_and_the_verified_payment(store):
    initial = store.register("i", PROFILE, 100)
    assert store.mark_claim("i")["claimed_paid"] is True
    assert store.set_callback("i", CALLBACK) == {**initial, "claimed_paid": True, "callback_at": CALLBACK}
    store.record_payment("i", 37)
    later = "2026-11-25T10:00:00Z"
    expected = {**initial, "claimed_paid": True, "callback_at": later, "paid_paise": 37}
    assert store.set_callback("i", later) == expected
    assert store.mark_claim("i") == expected
    assert store.get("i") == expected


@pytest.mark.parametrize("invalid", [None, "tomorrow", "2026-02-30T10:00:00Z", "2026-11-25T10:00:00"])
def test_invalid_callback_keeps_previous_schedule(store, invalid):
    store.register("i", PROFILE, 100)
    store.set_callback("i", CALLBACK)
    with pytest.raises(ValueError):
        store.set_callback("i", invalid)
    assert store.get("i")["callback_at"] == CALLBACK


@pytest.mark.parametrize("method,args", [("record_payment", (40,)), ("record_payment", (2**63,)), ("mark_claim", ()),
                                         ("set_callback", (CALLBACK,)), ("set_callback", ("invalid",))])
def test_unknown_updates_raise_key_error_without_creating_installment(store, method, args):
    with pytest.raises(KeyError):
        getattr(store, method)("missing", *args)
    assert store.all_installments() == []


def test_reimport_accepts_original_or_verified_remaining_and_keeps_identity_and_holds(store):
    original = store.register("i", PROFILE, 5000)
    store.record_payment("i", 2301)
    store.mark_claim("i")
    store.set_callback("i", CALLBACK)
    expected = {**original, "paid_paise": 2301, "claimed_paid": True, "callback_at": CALLBACK}
    edited = {**PROFILE, "customer_id": "new", "name": "Changed", "due_date": "2026-11-28"}
    assert store.register("i", edited, 2699) == expected
    assert store.register("i", edited, 5000) == expected
    assert store.all_installments() == [expected]
    store.record_payment("i", 5000)
    assert store.register("i", edited, 0) == {**expected, "paid_paise": 5000}


@pytest.mark.parametrize("phone,amount", [("8765432109", 100), ("9876543210", 39), ("9876543210", 0)])
def test_conflicting_import_never_changes_existing_record(store, phone, amount):
    store.register("i", PROFILE, 100)
    prior = store.record_payment("i", 40)
    with pytest.raises(ValueError):
        store.register("i", {**PROFILE, "phone_number": phone}, amount)
    assert store.all_installments() == [prior]


def test_fresh_process_preserves_holds_and_ignores_a_late_refresh(store):
    original = store.register("i", PROFILE, 100)
    store.record_payment("i", 37)
    store.mark_claim("i")
    store.set_callback("i", CALLBACK)
    output = subprocess.check_output(
        [sys.executable, "-c", "import json, payment_store as s; print(json.dumps(s.record_payment('i', 20)))"],
        cwd=Path(store.__file__).parent, text=True,
    )
    expected = {**original, "paid_paise": 37, "claimed_paid": True, "callback_at": CALLBACK}
    assert json.loads(output) == expected
    assert store.get("i") == expected


def race(*operations):
    barrier = Barrier(len(operations), timeout=10)

    def start(operation):
        barrier.wait()
        return operation()

    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        return list(pool.map(start, operations))


def test_concurrent_conflicting_first_imports_choose_one_intact_record(store):
    def attempt(phone, amount):
        try:
            return store.register("i", {**PROFILE, "phone_number": phone}, amount)
        except ValueError:
            return None

    results = race(partial(attempt, "9876543210", 100), partial(attempt, "8765432109", 250))
    assert results.count(None) == 1
    winner = store.get("i")
    assert (winner["phone_number"], winner["amount_paise"]) in [("9876543210", 100), ("8765432109", 250)]
    assert winner in results
    assert store.all_installments() == [winner]


def test_concurrent_refreshes_reimport_and_holds_keep_every_update(store):
    original = store.register("i", PROFILE, 100)
    race(partial(store.record_payment, "i", 20), partial(store.record_payment, "i", 90),
         partial(store.record_payment, "i", 5), partial(store.mark_claim, "i"),
         partial(store.set_callback, "i", CALLBACK), partial(store.register, "i", PROFILE, 100))
    assert store.all_installments() == [{**original, "paid_paise": 90, "claimed_paid": True, "callback_at": CALLBACK}]
