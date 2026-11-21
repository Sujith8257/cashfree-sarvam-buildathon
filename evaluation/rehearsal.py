"""Run a synthetic two-hour collections story through the local API in seconds."""
import base64
import hmac
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import requests
from fastapi.testclient import TestClient


def main():
    print('OFFLINE REHEARSAL | NO NETWORK | synthetic borrowers, clock and Cashfree responses')
    server_key, pg_secret = 'local-rehearsal', 'signed-fixture-only'
    root = Path(__file__).resolve().parents[1] / 'calltrigger-api'
    clock = datetime.fromisoformat('2026-11-21T12:00:00+05:30')
    amounts = iter([500, 500, 1200])

    def sandbox_reply(session, request, **kwargs):
        if request.method != 'GET' or request.url != 'https://sandbox.cashfree.com/pg/links/' + link:
            raise RuntimeError('The rehearsal never sends a real network request.')
        paid = next(amounts)
        r = requests.Response()
        r.status_code = 200
        r._content = json.dumps({'link_id': link, 'link_currency': 'INR', 'link_amount': 1200,
            'link_amount_paid': paid, 'link_status': 'PAID' if paid == 1200 else 'PARTIALLY_PAID',
            'customer_details': {'customer_phone': '9000000001'}}).encode()
        return r

    with (
        TemporaryDirectory() as tmp,
        patch.dict(os.environ, {'COLLECTIONS_DB': str(Path(tmp) / 'demo.sqlite3'), 'TRIGGER_API_KEY': server_key,
            'CASHFREE_PG_CLIENT_ID': 'demo-only', 'CASHFREE_PG_CLIENT_SECRET': pg_secret,'CALL_API_URL':'','SARVAM_API_KEY':''}),
        patch('dotenv.load_dotenv', return_value=False),
        patch.object(sys, 'path', [str(root), *sys.path]),
        patch.object(requests.Session, 'send', sandbox_reply),
    ):
        import trigger_api as api

        with (patch.object(api, 'TRIGGER_KEY', server_key), patch.object(api, 'now_ist', lambda: clock),
              TestClient(api.app, headers={'X-API-Key': server_key}) as client):
            def post(path, **kwargs):
                response = client.post(path, **kwargs)
                response.raise_for_status()
                return response

            def queue():
                response = client.get('/queue')
                response.raise_for_status()
                return response.json()

            ids = {}
            for i, (name, amount, days) in enumerate([('Meera', 1200, 5), ('Ravi', 800, 2), ('Anu', 400, 1)], 1):
                entry = post('/trigger/call?dry_run=true', json={'customer_id': f'DEMO-{i}', 'name': name,
                    'phone_number': f'900000000{i}', 'due_date': (clock.date()-timedelta(days=days)).isoformat(),
                    'outstanding_amount': amount}).json()
                ids[name] = entry['installment_id']
            print('Call next:', ' > '.join(r['name'] for r in queue()['call_queue']))
            promise = post(f"/queue/{ids['Ravi']}/promise", json={'amount':'250',
                           'promise_at':(clock+timedelta(hours=1)).isoformat()}).json()
            stop = post(f"/queue/{ids['Anu']}/contact-preference", json={'reason':'no_contact'}).json()
            print(f"Ravi: {promise['status']}; Anu: {stop['status']} (no calls)")

            link = 'emi-' + ids['Meera']
            for label, state in [('Meera','PARTIALLY_PAID'), ('Repeat','PARTIALLY_PAID'), ('Meera','PAID')]:
                # Sign the exact body. Money comes from sandbox_reply, not this notification.
                body = json.dumps({'type':'PAYMENT_LINK_EVENT','data':{'link_id':link, 'link_status':state}}).encode()
                timestamp = str(int(clock.timestamp()*1000))
                sig = base64.b64encode(hmac.digest(pg_secret.encode(),timestamp.encode()+body,'sha256')).decode()
                post('/webhooks/cashfree/payment-link', content=body, headers={'Content-Type':'application/json',
                     'x-webhook-timestamp':timestamp,'x-webhook-signature':sig})
                snapshot = queue()
                meera, = (r for r in snapshot['call_queue'] + snapshot['other'] if r['installment_id'] == ids['Meera'])
                print(f"{label}: INR {meera['outstanding_amount']:.2f} remaining")
            print(f"Meera: {meera['status']} (confirmed by fixture lookup)")
            clock += timedelta(hours=2)
            first, = queue()['call_queue']
            if 'lapsed' not in first['reason'].lower():
                raise RuntimeError('No lapsed promise in the eligible queue')
            print(f"{first['name']}: first after lapse. {first['reason'].replace('₹', 'INR ')}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
