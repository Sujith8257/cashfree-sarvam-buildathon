import io
import json
import os
import wave

import pytest
import requests
from fastapi.testclient import TestClient

os.environ.setdefault("TRIGGER_API_KEY", "test-trigger-key")
import trigger_api as api


NOTE = "Salary 5th ko aayegi. Maine branch mein de diya."


@pytest.fixture
def review(tmp_path, monkeypatch):
    monkeypatch.setenv("COLLECTIONS_DB", str(tmp_path / "demo.sqlite3"))
    monkeypatch.setenv("SARVAM_API_KEY", "dummy")
    monkeypatch.setattr(api, "TRIGGER_KEY", "fixture-trigger")
    cid = api.check_and_call({"customer_id":"fixture", "name":"Test", "phone_number":"9000000000",
                              "outstanding_amount":1200, "due_date":"2026-01-01"}, dry_run=True)["installment_id"]
    replies, urls = [], []
    def fixture_http(self, req, **kwargs):
        assert req.url in ('https://api.sarvam.ai/speech-to-text', 'https://api.sarvam.ai/v1/chat/completions')
        urls.append(req.url.rsplit('/', 1)[-1])
        result = requests.Response(); result.status_code = 200
        result._content = json.dumps(replies.pop(0)).encode()
        return result
    monkeypatch.setattr(requests.Session, 'send', fixture_http)
    return TestClient(api.app, headers={'X-API-Key':'fixture-trigger'}), '/queue/'+cid+'/review-note', replies, urls


def proposed(*signals):
    content = json.dumps({'signals':[{'kind':kind,'quote':quote} for kind,quote in signals]})
    return {'choices':[{'finish_reason':'stop','message':{'content':content}}]}


def test_signed_in_lender_gets_exact_quotes_not_synthetic_claims_or_money_movements(review):
    client, route, replies, calls = review
    replies.append(proposed(('salary_timing','Salary 5th ko aayegi'),('already_paid_claim','branch mein de diya'),
                            ('promise_to_pay','I will pay 1000 on Friday'),('score_high','5th'),
                            ('already_paid_claim','branch mein de diya')))
    result = client.post(route, data={'note':NOTE})
    assert result.status_code == 200
    assert [(s['kind'],s['quote']) for s in result.json()['signals']] == [
        ('salary_timing','Salary 5th ko aayegi'),('already_paid_claim','branch mein de diya')]
    assert calls == ['completions'] and result.json()['review_only'] is True
    row, = api.store.all_installments()
    assert row['paid_paise'] == 0 and row['claimed_paid'] is False


def test_telephony_audio_review_maps_quote_to_saaras_phrase_timestamp(review):
    client, route, replies, urls = review
    replies.extend([{'transcript':NOTE, 'language_code':'hi-IN', 'timestamps':{
        'words':['Salary 5th ko aayegi.', 'Maine branch mein de diya.'],
        'start_time_seconds':[0.0,0.5], 'end_time_seconds':[0.5,1.0]}},
        proposed(('already_paid_claim', 'branch mein de diya'))])
    clip = io.BytesIO()
    with wave.open(clip, 'wb') as stream:
        stream.setparams((1,2,8000,0,'NONE','not compressed')); stream.writeframes(bytes(16000))
    r = client.post(route, files={'audio':('call.wav',clip.getvalue(),'audio/wav')})
    assert r.status_code == 200
    signal, = r.json()['signals']
    assert r.json()['transcript'] == NOTE and (signal['start_seconds'], signal['end_seconds']) == (0.5,1.0)
    assert urls == ['speech-to-text','completions']


def test_invalid_audio_and_unknown_installment_do_not_call_a_provider(review):
    client, route, _, urls = review
    assert client.post(route, files={'audio':('x.wav',b'not a recording','audio/wav')}).status_code == 422
    assert client.post('/queue/unknown/review-note', data={'note':NOTE}).status_code == 404
    assert client.post(route, data={'note':NOTE}, headers={'X-API-Key':'wrong'}).status_code == 401
    assert urls == []
