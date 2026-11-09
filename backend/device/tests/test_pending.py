"""Ferramenta de fila local presa: lista sem segredos e libera só o item indicado."""
from backend.device.pending import mark_confirmed, pending_rows
from backend.device.storage import Store


def make_store(tmp_path):
    store = Store(tmp_path / 'device.db')
    store.initialize()
    with store.db() as db:
        for sample, state, payload in (
            ('edebe413-0000-4000-8000-000000000001', 'pending', '{"state":"not_evaluable"}'),
            ('aaaa0000-0000-4000-8000-000000000002', 'confirmed', None),
        ):
            db.execute(
                "INSERT INTO sample_status(sample_id,confirmation,payload,claim_id,lease_token,updated_at) "
                "VALUES (?,?,?,?,?,'2026-11-09T12:00:00Z')",
                (sample, state, payload, 'claim-secret', 'lease-secret'),
            )
    return store


def test_lists_only_stuck_items_without_tokens(tmp_path):
    rows = pending_rows(make_store(tmp_path))
    assert [row['sample_id'][:8] for row in rows] == ['edebe413']
    assert rows[0]['has_payload'] == 1
    assert 'lease-secret' not in str(rows) and 'claim-secret' not in str(rows)


def test_mark_confirmed_releases_queue_by_prefix(tmp_path):
    store = make_store(tmp_path)
    assert mark_confirmed(store, 'edebe413') == 1
    assert pending_rows(store) == []
    with store.db() as db:
        row = db.execute("SELECT payload,lease_token,claim_id FROM sample_status WHERE sample_id LIKE 'edebe413%'").fetchone()
    assert tuple(row) == (None, None, None)
    assert mark_confirmed(store, 'naoexiste') == 0


def test_server_reprocessing_of_confirmed_sample_is_accepted(tmp_path):
    import pytest

    store = make_store(tmp_path)
    confirmed = 'aaaa0000-0000-4000-8000-000000000002'
    with store.db() as db:
        db.execute("UPDATE sample_status SET analysis_id='old-analysis' WHERE sample_id=?", (confirmed,))
    store.start_sample_work(confirmed, {'claim_id': 'new-claim', 'lease_token': 'new-lease'})
    with store.db() as db:
        row = db.execute('SELECT confirmation,analysis_id,payload FROM sample_status WHERE sample_id=?', (confirmed,)).fetchone()
    assert tuple(row) == ('processing', None, None)
    # Resultado ainda não confirmado continua protegido.
    with pytest.raises(RuntimeError, match='não será sobrescrita'):
        store.start_sample_work('edebe413-0000-4000-8000-000000000001', {'claim_id': 'x', 'lease_token': 'y'})
