"""Replay the real notebook dry run on a fixed synthetic book, then unblind its ledger."""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from functools import partial
from itertools import combinations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient


HERE = Path(__file__).resolve().parent
SNAPSHOT_FIELDS = {"customer_id", "name", "language", "phone_number", "due_date", "outstanding_amount"}
WINDOW = timedelta(days=7)


def fixture(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def timestamp(text):
    value = datetime.fromisoformat(text)
    if value.utcoffset() is None:
        raise ValueError("timestamps must include a UTC offset")
    return value


def preview(rows, at):
    """Return IDs in endpoint order. Only OCR, the clock, and external I/O are substituted."""
    if any(set(row) != SNAPSHOT_FIELDS for row in rows):
        raise ValueError("only the six documented snapshot fields may enter the preview")
    ids = [row["customer_id"] for row in rows]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(ids) != len(set(ids)):
        raise ValueError("each row needs a unique, nonempty synthetic loan ID")

    with (
        TemporaryDirectory() as tmp,
        patch.dict(os.environ, {"TRIGGER_API_KEY": "synthetic-only", "SARVAM_API_KEY": "synthetic-only",
                                "CALL_API_URL": "", "CALL_API_TOKEN": "",
                                "COLLECTIONS_DB": str(Path(tmp) / "queue.sqlite3")}),
        patch("dotenv.load_dotenv", return_value=False),
        patch.object(sys, "path", [str(HERE.parent / "calltrigger-api"), *sys.path]),
        patch("requests.sessions.Session.request", side_effect=RuntimeError("outbound HTTP disabled")),
    ):
        import trigger_api as api

        with (
            patch.object(api, "TRIGGER_KEY", "synthetic-only"),
            patch.object(api, "triggered", set(), create=True),
            patch.object(api, "read_notebook", return_value=rows),
            patch.object(api, "check_and_call", partial(api.check_and_call, now=at.astimezone(api.IST))),
            TestClient(api.app) as client,
        ):
            response = client.post("/trigger/notebook", headers={"X-API-Key": "synthetic-only"},
                                   data={"dry_run": "true"}, files={"file": ("synthetic.png", b"fixture", "image/png")})
            response.raise_for_status()
            body = response.json()
    queue = body["call_queue"]
    ranked = [r["customer_id"] for r in queue]
    eligible = [r["customer_id"] for r in body["results"] if r["status"] == "would_call"]
    if ([r["rank"] for r in queue] != list(range(1, len(queue) + 1)) or sorted(ranked) != sorted(eligible)
            or sorted(r["customer_id"] for r in body["results"]) != sorted(ids)):
        raise ValueError("endpoint queue/ranks do not match the eligible snapshot rows")
    return ranked


def freeze_orders(queue):
    """The baseline sees precisely the same eligible IDs, with no access to outcomes."""
    return {"ranked": tuple(queue), "loan_id": tuple(sorted(queue))}


def audit_swaps(rows, at, original):
    audit = {}
    for fields in (("name",), ("language",), ("name", "language")):
        stats = {"checked": 0, "eligible_ties": 0, "changed": []}
        for i, j in combinations(range(len(rows)), 2):
            a, b = rows[i], rows[j]
            if any(a[f] == b[f] for f in fields):
                continue
            swapped = rows.copy()
            swapped[i] = {**a, **{f: b[f] for f in fields}}
            swapped[j] = {**b, **{f: a[f] for f in fields}}
            order = preview(swapped, at)
            pair = [a["customer_id"], b["customer_id"]]
            stats["checked"] += 1
            if a["due_date"] == b["due_date"] and all(loan in original for loan in pair):
                stats["eligible_ties"] += 1
            if order != original:
                stats["changed"].append({"pair": pair, "order": order})
        audit["+".join(fields)] = stats
    return audit


def compare(orders, outcomes, at, k):
    """Score frozen queues on incremental confirmed payments in (at, at + 7 days]."""
    if k < 0:
        raise ValueError("K must be nonnegative")
    end = at + WINDOW
    if timestamp(outcomes["observed_through"]) < end:
        raise ValueError("the ledger does not cover the full horizon")
    totals, seen = {}, set()
    for loan in orders["ranked"]:
        if loan not in outcomes["loans"]:
            raise ValueError(f"missing withheld outcomes for {loan}; use [] for observed no payment")
        total = 0
        for event in outcomes["loans"][loan]:
            if event["id"] in seen:
                raise ValueError(f"duplicate event ID: {event['id']}")
            seen.add(event["id"])
            if type(event["paise"]) is not int or event["paise"] <= 0 or event["status"] not in ("confirmed", "claimed"):
                raise ValueError(f"invalid synthetic ledger event: {event['id']}")
            if event["status"] == "confirmed" and at < timestamp(event["at"]) <= end:
                total += event["paise"]
        totals[loan] = total
    size = min(k, len(totals))
    report = {"as_of": at.isoformat(), "horizon_end": end.isoformat(), "requested_k": k,
              "eligible": len(totals), "effective_k": size}
    for method, order in orders.items():
        ids = list(order[:size])
        hits = sum(totals[loan] > 0 for loan in ids)
        report[method] = {"ids": ids, "hits": hits, "precision": hits / size if size else None,
                          "confirmed_paise": sum(totals[loan] for loan in ids)}
    return report


def evaluate(k):
    book = fixture("book.json")
    rows, at = book["rows"], timestamp(book["as_of"])
    ranked = preview(rows, at)
    orders = freeze_orders(ranked)
    swaps = audit_swaps(rows, at, ranked)
    # Only now open the outcome file: neither the endpoint nor any tie-break has seen it.
    return {"rows": len(rows), "swaps": swaps, **compare(orders, fixture("withheld_outcomes.json"), at, k)}


def format_report(r):
    lines = ["Synthetic notebook replay | seven-day horizon", f"Window: ({r['as_of']}, {r['horizon_end']}]",
             f"Rows: {r['rows']} | eligible: {r['eligible']} | requested K: {r['requested_k']} | selected: {r['effective_k']}",
             "Order      Hits   Precision   Confirmed INR   Selected loan IDs"]
    for key, label in (("ranked", "Preview"), ("loan_id", "Loan ID")):
        result = r[key]
        precision = "n/a" if result["precision"] is None else f"{result['precision']:.1%}"
        rupees, paise = divmod(result["confirmed_paise"], 100)
        amount = f"{rupees:,}.{paise:02d}"
        ids = ", ".join(result["ids"]) or "-"
        lines.append(f"{label:<10} {result['hits']:<6} {precision:<11} {amount:<15} {ids}")
    for variant, stats in r["swaps"].items():
        lines.append(f"Swap {variant}: {len(stats['changed'])}/{stats['checked']} orders changed; "
                     f"{stats['eligible_ties']} eligible equal-date pair(s) tested.")
        if stats["changed"]:
            lines.append(f"  First difference: {stats['changed'][0]}")
    return "\n".join([*lines, "Observed synthetic payments only; no causal effect or demographic fairness inferred."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=3, help="maximum loans per queue (default: 3)")
    parser.add_argument("--json", action="store_true", help="machine-readable report; currency in integer paise")
    args = parser.parse_args()
    if args.k < 0:
        parser.error("K must be nonnegative")
    report = evaluate(args.k)
    print(json.dumps(report, indent=2) if args.json else format_report(report))
    return int(any(a["changed"] for a in report["swaps"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
