import importlib


def test_judge_rehearsal_proves_payment_promise_and_contact_stop_with_no_network(capsys):
    try:
        replay = importlib.import_module('evaluation.rehearsal')
    except ModuleNotFoundError:
        replay = None
    assert replay is not None, 'Offline judge rehearsal is not implemented'
    assert replay.main() == 0
    lines = capsys.readouterr().out
    assert 'NO NETWORK' in lines
    assert 'Meera: INR 700.00' in lines and 'Repeat: INR 700.00' in lines
    assert 'Ravi: promise_wait' in lines and 'Ravi: first after lapse' in lines
    assert 'Anu: no_contact' in lines and 'Meera: paid' in lines
