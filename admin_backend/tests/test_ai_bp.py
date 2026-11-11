import json

import pytest
from sqlalchemy import text


AI_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    txn_date TEXT,
    description TEXT,
    amount REAL,
    db_cr TEXT,
    bank_code TEXT,
    mark_id TEXT,
    company_id TEXT,
    parent_id TEXT,
    updated_at TEXT,
    ai_suggested_mark_id TEXT,
    ai_confidence REAL,
    ai_source TEXT,
    ai_reason TEXT,
    ai_status TEXT,
    ai_suggested_at TEXT,
    ai_decided_at TEXT
);
CREATE TABLE IF NOT EXISTS marks (
    id TEXT PRIMARY KEY,
    internal_report TEXT,
    personal_use TEXT,
    tax_report TEXT,
    natural_direction TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS manual_journal_links (
    manual_txn_id TEXT,
    linked_txn_id TEXT
);
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture()
def ai_engine(engine):
    with engine.begin() as conn:
        for statement in AI_SCHEMA.split(';'):
            if statement.strip():
                conn.execute(text(statement))
    return engine


@pytest.fixture()
def ai_app(monkeypatch, ai_engine):
    from backend.routes import auth_bp as auth_bp_module
    from backend.routes.transactions import ai_bp as ai_bp_module

    monkeypatch.setattr(ai_bp_module, 'require_db_engine', lambda: ai_engine)
    monkeypatch.setattr(auth_bp_module, 'require_db_engine', lambda: ai_engine)
    auth_bp_module._active_user_cache.clear()

    from server import app as flask_app

    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture()
def ai_client(ai_app, make_user):
    make_user()
    client = ai_app.test_client()
    response = client.post('/api/auth/login', json={
        'email': 'admin@example.com', 'password': 'password123',
    })
    assert response.status_code == 200
    return client


def _insert_mark(ai_engine, mark_id='mark-beban', label='Belanja Bahan', direction=None):
    with ai_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO marks (id, internal_report, natural_direction) '
            'VALUES (:id, :label, :direction)'
        ), {'id': mark_id, 'label': label, 'direction': direction})


def _insert_transaction(ai_engine, txn_id='txn-1', description='TRSF E-BANKING 123 GOJEK',
                        db_cr='DB', mark_id=None, parent_id=None):
    with ai_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, mark_id, parent_id) '
            'VALUES (:id, :txn_date, :description, :amount, :db_cr, :bank_code, :mark_id, :parent_id)'
        ), {
            'id': txn_id, 'txn_date': '2026-01-15', 'description': description,
            'amount': 150000, 'db_cr': db_cr, 'bank_code': 'BCA',
            'mark_id': mark_id, 'parent_id': parent_id,
        })


def _enable_ai(ai_engine, enabled=True, model='qwen2.5:7b'):
    with ai_engine.begin() as conn:
        conn.execute(text('DELETE FROM app_settings'))
        conn.execute(text(
            'INSERT INTO app_settings (setting_key, setting_value) VALUES '
            "('ai_enabled', :enabled), ('ai_provider', 'lmstudio'), "
            "('ai_base_url', 'http://localhost:1234/v1'), ('ai_model', :model)"
        ), {'enabled': 'true' if enabled else 'false', 'model': model})


def _stub_llm(monkeypatch, payload):
    """Stub chat_completion: payload berupa dict, string mentah, atau Exception."""
    from backend.services.ai import llm_client

    calls = []

    def fake_chat_completion(**kwargs):
        calls.append(kwargs)
        if isinstance(payload, Exception):
            raise payload
        if isinstance(payload, str):
            return payload
        return json.dumps(payload)

    monkeypatch.setattr(llm_client, 'chat_completion', fake_chat_completion)
    return calls


def _txn_row(ai_engine, txn_id='txn-1'):
    with ai_engine.connect() as conn:
        row = conn.execute(text(
            'SELECT mark_id, ai_suggested_mark_id, ai_confidence, ai_status, ai_reason '
            'FROM transactions WHERE id = :txn_id'
        ), {'txn_id': txn_id}).fetchone()
    return dict(row._mapping) if row else None


# ---------------------------------------------------------------- settings


def test_settings_defaults(ai_client):
    response = ai_client.get('/api/ai/settings')
    assert response.status_code == 200
    settings = response.get_json()['settings']
    assert settings['enabled'] is False
    assert settings['provider'] == 'lmstudio'
    assert settings['base_url'] == 'http://localhost:1234/v1'


def test_settings_put_rejects_unknown_provider(ai_client):
    response = ai_client.put('/api/ai/settings', json={
        'enabled': True, 'provider': 'chatgpt',
        'base_url': 'http://localhost:1234/v1', 'model': 'x',
    })
    assert response.status_code == 400


def test_settings_put_rejects_missing_base_url(ai_client):
    response = ai_client.put('/api/ai/settings', json={
        'enabled': True, 'provider': 'lmstudio', 'base_url': '   ', 'model': 'x',
    })
    assert response.status_code == 400


def test_settings_put_normalizes_and_saves(ai_client):
    response = ai_client.put('/api/ai/settings', json={
        'enabled': True, 'provider': 'ollama',
        'base_url': 'localhost:11434/v1/', 'model': 'qwen2.5:7b',
    })
    assert response.status_code == 200
    assert response.get_json()['settings'] == {
        'enabled': True,
        'provider': 'ollama',
        'base_url': 'http://localhost:11434/v1',
        'model': 'qwen2.5:7b',
        'timeout': 120,
        'auto_apply': False,
        'auto_apply_threshold': 0.9,
        'bridge': True,  # provider ollama → bridge
        'api_key_set': False,
    }

    follow_up = ai_client.get('/api/ai/settings')
    assert follow_up.get_json()['settings']['enabled'] is True


def test_settings_tidak_lagi_menerima_api_key(ai_client):
    """AI key kini milik vault (PUT /api/credentials) — /api/ai/settings mengabaikannya."""
    resp = ai_client.put('/api/ai/settings', json={
        'enabled': True,
        'provider': 'zai',
        'base_url': 'https://api.z.ai/api/paas/v4',
        'model': 'glm-4',
        'auto_apply': False,
        'auto_apply_threshold': 0.9,
        'api_key': 'secret-key-12345',
    })
    assert resp.status_code == 200
    settings = resp.get_json()['settings']
    assert settings['api_key_set'] is False  # kunci tidak ditulis lewat endpoint ini
    assert 'api_key' not in settings

    follow_up = ai_client.get('/api/ai/settings').get_json()['settings']
    assert follow_up['api_key_set'] is False


def test_auto_apply_settings_roundtrip(ai_client):
    response = ai_client.put('/api/ai/settings', json={
        'enabled': True, 'provider': 'ollama',
        'base_url': 'http://localhost:11434/v1', 'model': 'qwen2.5:7b',
        'auto_apply': True, 'auto_apply_threshold': 0.85,
    })
    settings = response.get_json()['settings']
    assert settings['auto_apply'] is True
    assert settings['auto_apply_threshold'] == 0.85

    # Threshold di luar [0,1] dikembalikan ke batas.
    clamped = ai_client.put('/api/ai/settings', json={
        'enabled': True, 'provider': 'ollama',
        'base_url': 'http://localhost:11434/v1', 'model': 'qwen2.5:7b',
        'auto_apply': True, 'auto_apply_threshold': 5,
    }).get_json()['settings']
    assert clamped['auto_apply_threshold'] == 1.0


# ---------------------------------------------------------------- suggest


def test_suggest_requires_enabled(ai_client, ai_engine):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine)
    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']})
    assert response.status_code == 400
    assert response.get_json()['code'] == 'ai_disabled'


def test_suggest_rejects_empty_and_oversized_batch(ai_client, ai_engine):
    assert ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': []}).status_code == 400

    ids = [f'txn-{i}' for i in range(16)]
    assert ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ids}).status_code == 400


def test_suggest_stores_pending_and_keeps_mark_id(ai_client, ai_engine, monkeypatch):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine, mark_id=None)
    _enable_ai(ai_engine)
    calls = _stub_llm(monkeypatch, {
        'mark_id': 'mark-beban', 'confidence': 0.9, 'reason': 'Transfer Gojek adalah beban operasional.',
    })

    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']})
    assert response.status_code == 200
    body = response.get_json()
    assert body['suggested_count'] == 1
    result = body['results'][0]
    assert result['status'] == 'suggested'
    assert result['ai_suggested_mark_id'] == 'mark-beban'

    # Prompt memakai konteks transaksi + kandidat mark.
    assert len(calls) == 1
    user_content = calls[0]['messages'][1]['content']
    assert 'GOJEK' in user_content
    assert 'mark-beban' in user_content

    row = _txn_row(ai_engine)
    assert row['mark_id'] is None  # mark_id tidak berubah sebelum review
    assert row['ai_suggested_mark_id'] == 'mark-beban'
    assert row['ai_status'] == 'pending'


def test_suggest_reports_invalid_ai_output(ai_client, ai_engine, monkeypatch):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine)
    _enable_ai(ai_engine)
    _stub_llm(monkeypatch, 'Maaf, saya tidak bisa menjawab.')

    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']})
    assert response.status_code == 200
    body = response.get_json()
    assert body['suggested_count'] == 0
    assert body['failed_count'] == 1
    assert body['results'][0]['status'] == 'failed'


def test_suggest_accepts_label_instead_of_id(ai_client, ai_engine, monkeypatch):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine)
    _enable_ai(ai_engine)
    _stub_llm(monkeypatch, {'mark_id': 'Belanja Bahan', 'confidence': 1.4, 'reason': ''})

    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']})
    body = response.get_json()
    assert body['suggested_count'] == 1
    row = _txn_row(ai_engine)
    assert row['ai_suggested_mark_id'] == 'mark-beban'
    assert row['ai_confidence'] == 1.0  # clamp ke [0, 1]


def test_suggest_skips_split_parent(ai_client, ai_engine, monkeypatch):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine, txn_id='txn-parent')
    _insert_transaction(ai_engine, txn_id='txn-child', parent_id='txn-parent')
    _enable_ai(ai_engine)
    _stub_llm(monkeypatch, {'mark_id': 'mark-beban', 'confidence': 0.9, 'reason': 'ok'})

    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-parent']})
    body = response.get_json()
    assert body['skipped_count'] == 1
    assert 'split' in body['results'][0]['reason'].lower()


def test_suggest_surfaces_connection_error(ai_client, ai_engine, monkeypatch):
    from backend.services.ai import llm_client

    _insert_mark(ai_engine)
    _insert_transaction(ai_engine)
    _enable_ai(ai_engine)
    _stub_llm(monkeypatch, llm_client.LLMConnectionError('Server AI tidak dapat dihubungi.'))

    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']})
    body = response.get_json()
    assert body['failed_count'] == 1
    assert 'tidak dapat dihubungi' in body['results'][0]['error']


# ---------------------------------------------------------------- rule engine (data existing)


def test_normalize_description_strips_noise():
    from backend.services.ai.mark_suggester import normalize_description

    assert normalize_description('TRSF E-BANKING DB 2102/FTSCY/WS95271  2315326.00 FLIPTECH') == \
        'TRSF E BANKING DB FTSCY WS FLIPTECH'
    assert normalize_description('TRANSAKSI DEBIT TGL: 08/02  QR 899 00000.00PT Tokoped') == \
        'TRANSAKSI DEBIT TGL QR PT TOKOPED'
    assert normalize_description(None) == ''


def test_suggest_prefers_history_rule_without_llm(ai_client, ai_engine, monkeypatch):
    """Deskripsi identik dengan riwayat ber-mark → saran dari data user, LLM tidak dipanggil."""
    from backend.services.ai import llm_client

    _insert_mark(ai_engine)
    _enable_ai(ai_engine)
    with ai_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, mark_id) '
            "VALUES ('hist-1', '2025-06-01', 'TRSF E-BANKING 9999 GOJEK TOPUP', 100000, 'DB', 'BCA', 'mark-beban')"
        ))
    _insert_transaction(ai_engine, txn_id='txn-1',
                        description='TRSF E-BANKING 8888 GOJEK TOPUP', db_cr='DB')

    def fail_if_called(**kwargs):
        raise AssertionError('LLM tidak seharusnya dipanggil ketika pola riwayat kuat')

    monkeypatch.setattr(llm_client, 'chat_completion', fail_if_called)

    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']})
    body = response.get_json()
    assert body['suggested_count'] == 1
    result = body['results'][0]
    assert result['ai_source'] == 'rule'
    assert result['ai_suggested_mark_id'] == 'mark-beban'
    assert 'transaksi serupa' in result['ai_reason'] or 'identik' in result['ai_reason']

    row = _txn_row(ai_engine)
    assert row['ai_status'] == 'pending'


def test_llm_prompt_includes_history_examples(ai_client, ai_engine, monkeypatch):
    """Tanpa kecocokan persis → LLM dipanggil dengan contoh riwayat user (few-shot)."""
    _insert_mark(ai_engine)
    _enable_ai(ai_engine)
    with ai_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, mark_id) '
            "VALUES ('hist-1', '2025-06-01', 'BELANJA LISTRIK PLN 11112222', 200000, 'DB', 'BCA', 'mark-beban')"
        ))
    _insert_transaction(ai_engine, txn_id='txn-1', description='KERETA API KAI 5555', db_cr='DB')

    captured = {}
    def fake_chat_completion(**kwargs):
        captured.update(kwargs)
        return '{"mark_id": "mark-beban", "confidence": 0.7, "reason": "mengikuti contoh"}'

    from backend.services.ai import llm_client
    monkeypatch.setattr(llm_client, 'chat_completion', fake_chat_completion)

    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']})
    body = response.get_json()
    assert body['suggested_count'] == 1
    assert body['results'][0]['ai_source'] == 'llm'

    user_content = captured['messages'][1]['content']
    assert 'Pola penandaan dari data Anda sendiri' in user_content
    assert 'BELANJA LISTRIK PLN 11112222' in user_content
    assert 'mark-beban' in user_content


# ---------------------------------------------------------------- fuzzy & recurring


def test_fuzzy_similar_description_suggests_from_history(ai_client, ai_engine, monkeypatch):
    """Deskripsi mirip (bukan identik) → rule menyimpulkan dari riwayat, confidence dibatasi."""
    from backend.services.ai import llm_client

    _insert_mark(ai_engine, mark_id='mark-gaji', label='Gaji Pegawai')
    _enable_ai(ai_engine)
    with ai_engine.begin() as conn:
        # Dua riwayat mirip (beda nomor referensi & nama penerima) ke mark yang sama.
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, mark_id) '
            "VALUES ('hist-1', '2025-06-01', 'NBMB DITYO ENGGAR K TO BUDI SANTOSO ESB:NBMB:0001500F:1111 Transfer Ke Budi via BRImo', 600000, 'DB', 'BRIBA', 'mark-gaji'),"
            "('hist-2', '2025-07-01', 'NBMB DITYO ENGGAR K TO CICI PERMATA ESB:NBMB:0001500F:2222 Transfer Ke Cici via BRImo', 650000, 'DB', 'BRIBA', 'mark-gaji')"
        ))
    _insert_transaction(ai_engine, txn_id='txn-1',
                        description='NBMB DITYO ENGGAR K TO RIKI ARIF RIYANTO ESB:NBMB:0001500F:3333 Transfer Ke Riki via BRImo',
                        db_cr='DB')

    def fail_if_called(**kwargs):
        raise AssertionError('Kemiripan >= ambang tidak seharusnya memanggil LLM')

    monkeypatch.setattr(llm_client, 'chat_completion', fail_if_called)

    body = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']}).get_json()
    assert body['suggested_count'] == 1
    result = body['results'][0]
    assert result['ai_source'] == 'rule'
    assert result['ai_suggested_mark_id'] == 'mark-gaji'
    assert result['ai_confidence'] <= 0.85  # fuzzy tidak pernah auto-apply di threshold bawaan
    assert 'Mirip' in result['ai_reason']


def test_split_exact_marks_surfaces_recurring_to_llm(ai_client, ai_engine, monkeypatch):
    """Deskripsi identik dipakai 2 mark → LLM menerima blok 'PERSIS sama' dgn rentang nominal."""
    _insert_mark(ai_engine, mark_id='mark-gaji', label='Gaji Pegawai')
    _insert_mark(ai_engine, mark_id='mark-warung', label='Pembelian Warung')
    _enable_ai(ai_engine)
    with ai_engine.begin() as conn:
        # Deskripsi identik (normalisasi menyamakan nomor referensi), mark terbagi + nominal beda.
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, mark_id) VALUES '
            "('h1', '2025-06-01', 'NBMB DITYO ENGGAR K TO RIKI ESB:NBMB:0001500F:1111 Transfer Ke Riki via BRImo', 1800000, 'DB', 'BRIBA', 'mark-gaji'),"
            "('h2', '2025-06-02', 'NBMB DITYO ENGGAR K TO RIKI ESB:NBMB:0001500F:2222 Transfer Ke Riki via BRImo', 2100000, 'DB', 'BRIBA', 'mark-gaji'),"
            "('h3', '2025-07-01', 'NBMB DITYO ENGGAR K TO RIKI ESB:NBMB:0001500F:3333 Transfer Ke Riki via BRImo', 150000, 'DB', 'BRIBA', 'mark-warung'),"
            "('h4', '2025-07-02', 'NBMB DITYO ENGGAR K TO RIKI ESB:NBMB:0001500F:4444 Transfer Ke Riki via BRImo', 90000, 'DB', 'BRIBA', 'mark-warung')"
        ))
    _insert_transaction(ai_engine, txn_id='txn-1',
                        description='NBMB DITYO ENGGAR K TO RIKI ESB:NBMB:0001500F:5555 Transfer Ke Riki via BRImo',
                        db_cr='DB')

    captured = {}
    def fake_chat_completion(**kwargs):
        captured.update(kwargs)
        return '{"mark_id": "mark-warung", "confidence": 0.75, "reason": "nominal kecil seperti pembelian warung"}'

    from backend.services.ai import llm_client
    monkeypatch.setattr(llm_client, 'chat_completion', fake_chat_completion)

    body = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']}).get_json()
    assert body['suggested_count'] == 1
    assert body['results'][0]['ai_source'] == 'llm'

    user_content = captured['messages'][1]['content']
    assert 'PERSIS sama' in user_content
    assert 'Gaji Pegawai' in user_content and 'Pembelian Warung' in user_content
    assert 'nominal' in user_content
    # Contoh few-shot menyertakan label dan nominal, bukan hanya UUID mentah.
    assert 'Gaji Pegawai [' in user_content
    assert '1.800.000' in user_content or '2.100.000' in user_content


# ---------------------------------------------------------------- decision


def _request_suggestion(ai_client, monkeypatch):
    """Ajukan saran untuk txn-1 dengan stub LLM deterministik."""
    _stub_llm(monkeypatch, {'mark_id': 'mark-beban', 'confidence': 0.85, 'reason': 'pola beban'})
    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']})
    assert response.get_json()['suggested_count'] == 1


def test_accept_sets_mark_and_status(ai_client, ai_engine, monkeypatch):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine)
    _enable_ai(ai_engine)
    _request_suggestion(ai_client, monkeypatch)

    response = ai_client.post('/api/transactions/txn-1/ai-decision', json={'decision': 'accept'})
    assert response.status_code == 200
    txn = response.get_json()['transaction']
    assert txn['mark_id'] == 'mark-beban'
    assert txn['ai_status'] == 'accepted'

    row = _txn_row(ai_engine)
    assert row['mark_id'] == 'mark-beban'
    assert row['ai_status'] == 'accepted'


def test_reject_keeps_mark_empty(ai_client, ai_engine, monkeypatch):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine)
    _enable_ai(ai_engine)
    _request_suggestion(ai_client, monkeypatch)

    response = ai_client.post('/api/transactions/txn-1/ai-decision', json={'decision': 'reject'})
    assert response.status_code == 200
    row = _txn_row(ai_engine)
    assert row['mark_id'] is None
    assert row['ai_status'] == 'rejected'
    assert row['ai_suggested_mark_id'] == 'mark-beban'  # audit trail tetap ada


def test_accept_blocked_for_manual_linked(ai_client, ai_engine, monkeypatch):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine)
    _enable_ai(ai_engine)
    _request_suggestion(ai_client, monkeypatch)

    # Link manual muncul setelah saran dibuat (misal user membuat journal di sela review).
    with ai_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO manual_journal_links (manual_txn_id, linked_txn_id) '
            "VALUES ('manual-1', 'txn-1')"
        ))

    response = ai_client.post('/api/transactions/txn-1/ai-decision', json={'decision': 'accept'})
    assert response.status_code == 400
    assert 'manual journal' in response.get_json()['error']


def test_decision_requires_valid_value(ai_client):
    response = ai_client.post('/api/transactions/txn-1/ai-decision', json={'decision': 'maybe'})
    assert response.status_code == 400


def test_decision_without_suggestion(ai_client, ai_engine):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine)
    response = ai_client.post('/api/transactions/txn-1/ai-decision', json={'decision': 'accept'})
    assert response.status_code == 400
    assert response.get_json()['code'] == 'ai_no_suggestion'


# ---------------------------------------------------------------- auto-apply & bulk


def _enable_auto_apply(ai_engine, threshold=0.9):
    with ai_engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES ('ai_auto_apply', 'true') "
            "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value"
        ))
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES ('ai_auto_apply_threshold', :t) "
            "ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value"
        ), {'t': str(threshold)})


def test_rule_auto_applies_when_enabled(ai_client, ai_engine, monkeypatch):
    """Kecocokan riwayat + auto_apply aktif → mark langsung terisi, status auto_applied."""
    from backend.services.ai import llm_client

    _insert_mark(ai_engine)
    _enable_ai(ai_engine)
    _enable_auto_apply(ai_engine)
    with ai_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, mark_id) '
            "VALUES ('hist-1', '2025-06-01', 'BIAYA ADM 12345', 5000, 'DB', 'BCA', 'mark-beban')"
        ))
    _insert_transaction(ai_engine, txn_id='txn-1', description='BIAYA ADM 67890', db_cr='DB')

    def fail_if_called(**kwargs):
        raise AssertionError('Rule match kuat tidak seharusnya memanggil LLM')

    monkeypatch.setattr(llm_client, 'chat_completion', fail_if_called)

    response = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']})
    body = response.get_json()
    assert body['auto_applied_count'] == 1
    assert body['results'][0]['status'] == 'auto_applied'

    row = _txn_row(ai_engine)
    assert row['mark_id'] == 'mark-beban'       # langsung masuk ke marked
    assert row['ai_status'] == 'auto_applied'   # tetap bertanda AI


def test_rule_stays_pending_when_auto_apply_off(ai_client, ai_engine, monkeypatch):
    _insert_mark(ai_engine)
    _enable_ai(ai_engine)  # auto_apply default false
    with ai_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, mark_id) '
            "VALUES ('hist-1', '2025-06-01', 'BIAYA ADM 12345', 5000, 'DB', 'BCA', 'mark-beban')"
        ))
    _insert_transaction(ai_engine, txn_id='txn-1', description='BIAYA ADM 67890', db_cr='DB')

    from backend.services.ai import llm_client
    monkeypatch.setattr(llm_client, 'chat_completion',
                        lambda **k: (_ for _ in ()).throw(AssertionError('LLM tidak boleh dipanggil')))

    body = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']}).get_json()
    assert body['auto_applied_count'] == 0
    assert body['suggested_count'] == 1
    row = _txn_row(ai_engine)
    assert row['mark_id'] is None
    assert row['ai_status'] == 'pending'


def test_llm_suggestion_never_auto_applies(ai_client, ai_engine, monkeypatch):
    """Saran LLM selalu pending meski confidence tinggi & auto_apply aktif."""
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine, description='KERETA API KAI 9999', db_cr='DB')
    _enable_ai(ai_engine)
    _enable_auto_apply(ai_engine)
    _stub_llm(monkeypatch, {'mark_id': 'mark-beban', 'confidence': 1.0, 'reason': 'ok'})

    body = ai_client.post('/api/transactions/ai-suggest', json={'transaction_ids': ['txn-1']}).get_json()
    assert body['suggested_count'] == 1
    assert body['auto_applied_count'] == 0
    row = _txn_row(ai_engine)
    assert row['mark_id'] is None
    assert row['ai_status'] == 'pending'


def test_bulk_accept_and_reject_undo(ai_client, ai_engine, monkeypatch):
    global ai_client_global  # noqa — tidak dipakai; helper di bawah pakai ai_client lokal
    _insert_mark(ai_engine)
    _enable_ai(ai_engine)
    with ai_engine.begin() as conn:
        # Dua transaksi dengan riwayat serupa → rule match saat di-suggest.
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, mark_id) '
            "VALUES ('hist-1', '2025-06-01', 'BIAYA ADM 12345', 5000, 'DB', 'BCA', 'mark-beban')"
        ))
    _insert_transaction(ai_engine, txn_id='txn-a', description='BIAYA ADM 111', db_cr='DB')
    _insert_transaction(ai_engine, txn_id='txn-b', description='BIAYA ADM 222', db_cr='DB')

    from backend.services.ai import llm_client
    monkeypatch.setattr(llm_client, 'chat_completion',
                        lambda **k: (_ for _ in ()).throw(AssertionError('LLM tidak boleh dipanggil')))

    body = ai_client.post('/api/transactions/ai-suggest', json={
        'transaction_ids': ['txn-a', 'txn-b'],
    }).get_json()
    assert body['suggested_count'] == 2

    # Bulk accept → keduanya langsung ter-mark.
    bulk = ai_client.post('/api/transactions/ai-decision-bulk', json={
        'decision': 'accept', 'transaction_ids': ['txn-a', 'txn-b'],
    }).get_json()
    assert bulk['updated'] == 2
    with ai_engine.connect() as conn:
        marks = conn.execute(text(
            "SELECT COUNT(*) FROM transactions WHERE mark_id = 'mark-beban' AND id IN ('txn-a', 'txn-b')"
        )).scalar_one()
    assert marks == 2

    # Reject pada baris accepted → mark tetap (accept idempoten, reject bekerja di pending/auto).
    # Auto-applied reject → undo (mark dikosongkan): simulasi dengan status auto_applied.
    with ai_engine.begin() as conn:
        conn.execute(text("UPDATE transactions SET ai_status = 'auto_applied' WHERE id = 'txn-a'"))
    undo = ai_client.post('/api/transactions/ai-decision-bulk', json={
        'decision': 'reject', 'transaction_ids': ['txn-a'],
    }).get_json()
    assert undo['updated'] == 1
    with ai_engine.connect() as conn:
        row = conn.execute(text(
            "SELECT mark_id, ai_status FROM transactions WHERE id = 'txn-a'"
        )).fetchone()
    assert row[0] is None and row[1] == 'rejected'


# ---------------------------------------------------------------- unit: kandidat


def test_load_candidate_marks_orders_by_direction(ai_engine):
    """Semua mark berlabel masuk kandidat; mark arah-cocok tampil sebelum berlawanan.

    Mark berlawanan arah tetap ikut — pembalikan tanda ditangani sistem (migration 043).
    """
    from backend.services.ai.mark_suggester import load_candidate_marks

    _insert_mark(ai_engine, mark_id='m-db', label='Beban', direction='DB')
    _insert_mark(ai_engine, mark_id='m-cr', label='Pendapatan', direction='CR')
    _insert_mark(ai_engine, mark_id='m-any', label='Umum', direction=None)

    with ai_engine.connect() as conn:
        db_candidates = load_candidate_marks(conn, 'DB')
        cr_ids = [c['id'] for c in load_candidate_marks(conn, 'CR')]

    db_ids = [c['id'] for c in db_candidates]
    # Semua mark berlabel ikut sebagai kandidat.
    assert set(db_ids) == {'m-db', 'm-cr', 'm-any'}
    # Mark arah-cocok mendapat prioritas urutan.
    assert db_ids[0] == 'm-db'
    assert cr_ids[0] == 'm-cr'


def test_settings_expose_bridge_flag(ai_client, ai_engine):
    """Provider lokal (lmstudio/ollama) → bridge=True; zai → bridge=False."""
    def _get():
        response = ai_client.get('/api/ai/settings')
        assert response.status_code == 200
        return response.get_json()['settings']

    # app_settings masih kosong → provider default 'lmstudio' → bridge True.
    assert _get()['bridge'] is True

    with ai_engine.begin() as conn:
        conn.execute(text('DELETE FROM app_settings'))
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES "
            "('ai_provider', 'zai'), ('ai_api_key', 'k')"
        ))
    assert _get()['bridge'] is False


# ---------------------------------------------------------------- unit: resolve_transaction_rules


def test_resolve_rules_returns_llm_prompt_without_calling_llm(ai_engine, monkeypatch):
    """Transaksi tanpa kecocokan riwayat → prompt LLM siap pakai, TANPA panggilan LLM."""
    from backend.services.ai import llm_client, mark_suggester

    _insert_mark(ai_engine)
    _insert_transaction(ai_engine, txn_id='txn-bridge', description='TRSF UNIK TANPA RIWAYAT')
    _enable_ai(ai_engine)

    def _explode(**kwargs):
        raise AssertionError('LLM TIDAK boleh dipanggil di tahap resolve')

    monkeypatch.setattr(llm_client, 'chat_completion', _explode)

    with ai_engine.connect() as conn:
        config = llm_client.get_ai_settings(conn)
        history_index = mark_suggester.build_history_index(conn)
        resolved = mark_suggester.resolve_transaction_rules(
            conn, 'txn-bridge', config, history_index=history_index,
        )

    assert resolved['kind'] == 'llm'
    prompt = resolved['prompt']
    assert prompt['id'] == 'txn-bridge'
    assert prompt['model'] == 'qwen2.5:7b'
    assert prompt['temperature'] == 0.1
    assert prompt['max_tokens'] == 800
    assert isinstance(prompt['messages'], list) and prompt['messages']
    assert 'api_key' not in prompt  # kunci z.ai tidak pernah masuk prompt bridge


def test_resolve_rules_rule_match_stores_and_finishes(ai_engine):
    """Kecocokan riwayat persis → result final tanpa LLM, saran tersimpan source=rule."""
    from backend.services.ai import llm_client, mark_suggester

    _insert_mark(ai_engine)
    _insert_transaction(ai_engine, txn_id='txn-hist-1', description='TRSF E-BANKING 123 GOJEK', mark_id='mark-beban')
    _insert_transaction(ai_engine, txn_id='txn-hist-2', description='TRSF E-BANKING 123 GOJEK')
    _enable_ai(ai_engine)

    with ai_engine.connect() as conn:
        config = llm_client.get_ai_settings(conn)
        history_index = mark_suggester.build_history_index(conn)
        resolved = mark_suggester.resolve_transaction_rules(
            conn, 'txn-hist-2', config, history_index=history_index,
        )

    assert resolved['kind'] == 'done'
    assert resolved['result']['status'] == 'suggested'
    assert resolved['result']['ai_source'] == 'rule'


# ---------------------------------------------------------------- prepare (bridge 1/2)


def test_prepare_resolves_rules_and_returns_pending(ai_client, ai_engine, monkeypatch):
    """Rule match → masuk results (tersimpan); tanpa kecocokan → pending prompt."""
    from backend.services.ai import llm_client

    def _explode(**kwargs):
        raise AssertionError('prepare TIDAK boleh memanggil LLM')

    monkeypatch.setattr(llm_client, 'chat_completion', _explode)

    _insert_mark(ai_engine)
    _insert_transaction(ai_engine, txn_id='txn-rule', description='TRSF E-BANKING 123 GOJEK', mark_id='mark-beban')
    _insert_transaction(ai_engine, txn_id='txn-llm', description='TRSF BARU TANPA RIWAYAT 999')
    _enable_ai(ai_engine)

    response = ai_client.post('/api/transactions/ai-suggest/prepare', json={
        'transaction_ids': ['txn-rule', 'txn-llm'],
    })
    assert response.status_code == 200
    data = response.get_json()
    assert [r['id'] for r in data['results']] == ['txn-rule']
    assert data['results'][0]['ai_source'] == 'rule'
    assert len(data['pending']) == 1
    prompt = data['pending'][0]
    assert prompt['id'] == 'txn-llm'
    assert prompt['model'] == 'qwen2.5:7b'
    assert isinstance(prompt['messages'], list) and prompt['messages']
    assert 'api_key' not in prompt

    # Rule sudah tersimpan di prepare (source=rule, pending review).
    with ai_engine.connect() as conn:
        status = conn.execute(text(
            "SELECT ai_suggested_mark_id, ai_source FROM transactions WHERE id='txn-rule'"
        )).fetchone()._mapping
    assert status['ai_suggested_mark_id'] == 'mark-beban'
    assert status['ai_source'] == 'rule'


def test_prepare_validates_and_guards(ai_client, ai_engine):
    """ai_disabled, batch kosong/oversize, id tak dikenal → perilaku endpoint lama."""
    _enable_ai(ai_engine, enabled=False)
    _insert_transaction(ai_engine, txn_id='txn-x')

    response = ai_client.post('/api/transactions/ai-suggest/prepare', json={'transaction_ids': ['txn-x']})
    assert response.status_code == 400
    assert response.get_json()['code'] == 'ai_disabled'

    _enable_ai(ai_engine)
    response = ai_client.post('/api/transactions/ai-suggest/prepare', json={'transaction_ids': []})
    assert response.status_code == 400
    response = ai_client.post('/api/transactions/ai-suggest/prepare', json={
        'transaction_ids': [f'txn-{i}' for i in range(16)]})
    assert response.status_code == 400

    # id tak dikenal → skipped di results, bukan error
    response = ai_client.post('/api/transactions/ai-suggest/prepare', json={'transaction_ids': ['tidak-ada']})
    assert response.status_code == 200
    assert response.get_json()['results'][0]['status'] == 'skipped'


# ---------------------------------------------------------------- submit (bridge 2/2)


def _prepare_one_pending(ai_client, ai_engine, txn_id='txn-sub'):
    _insert_mark(ai_engine)
    _insert_transaction(ai_engine, txn_id=txn_id, description='TRSF SUBMIT TANPA RIWAYAT 777')
    _enable_ai(ai_engine)
    response = ai_client.post('/api/transactions/ai-suggest/prepare', json={'transaction_ids': [txn_id]})
    assert response.status_code == 200
    assert len(response.get_json()['pending']) == 1


def test_submit_stores_valid_raw(ai_client, ai_engine):
    _prepare_one_pending(ai_client, ai_engine, 'txn-ok')
    raw = json.dumps({'mark_id': 'mark-beban', 'confidence': 0.87, 'reason': 'Kategori belanja'})
    response = ai_client.post('/api/transactions/ai-suggest/submit', json={
        'items': [{'id': 'txn-ok', 'raw': raw}]})
    assert response.status_code == 200
    data = response.get_json()
    assert data['suggested_count'] == 1 and data['failed_count'] == 0
    result = data['results'][0]
    assert result['status'] == 'suggested'
    assert result['ai_suggested_mark_id'] == 'mark-beban'
    assert result['ai_source'] == 'llm'
    assert 'auto_applied' not in result  # saran LLM tidak pernah auto-apply

    with ai_engine.connect() as conn:
        row = conn.execute(text(
            "SELECT ai_status, ai_source FROM transactions WHERE id='txn-ok'"
        )).fetchone()._mapping
    assert row['ai_status'] == 'pending' and row['ai_source'] == 'llm'


def test_submit_rejects_bad_raw_and_unknown_ids(ai_client, ai_engine):
    _prepare_one_pending(ai_client, ai_engine, 'txn-bad')

    response = ai_client.post('/api/transactions/ai-suggest/submit', json={'items': [
        {'id': 'txn-bad', 'raw': 'bukan json sama sekali'},        # parse gagal → failed
        {'id': 'tidak-ada', 'raw': '{"mark_id": "mark-beban"}'},   # transaksi hilang → skipped
        {'id': 'txn-err', 'error': 'Server AI tidak menjawab.'},   # error browser → failed
    ]})
    assert response.status_code == 200
    data = response.get_json()
    by_id = {r['id']: r for r in data['results']}
    assert by_id['txn-bad']['status'] == 'failed'
    assert by_id['tidak-ada']['status'] == 'skipped'
    assert by_id['txn-err']['status'] == 'failed'
    assert data['failed_count'] == 2 and data['skipped_count'] == 1

    # item gagal TIDAK menyimpan apa pun
    with ai_engine.connect() as conn:
        row = conn.execute(text(
            "SELECT ai_suggested_mark_id FROM transactions WHERE id='txn-bad'"
        )).fetchone()._mapping
    assert row['ai_suggested_mark_id'] is None


def test_submit_validates_mark_against_db_candidates(ai_client, ai_engine):
    """Browser tidak dipercaya: mark di luar kandidat DB → failed."""
    _prepare_one_pending(ai_client, ai_engine, 'txn-forged')
    raw = json.dumps({'mark_id': 'mark-palsu-dari-browser', 'confidence': 0.99})
    response = ai_client.post('/api/transactions/ai-suggest/submit', json={
        'items': [{'id': 'txn-forged', 'raw': raw}]})
    data = response.get_json()
    assert data['results'][0]['status'] == 'failed'
    assert data['failed_count'] == 1


def test_submit_rejects_bad_body(ai_client, ai_engine):
    response = ai_client.post('/api/transactions/ai-suggest/submit', json={'items': []})
    assert response.status_code == 400
    response = ai_client.post('/api/transactions/ai-suggest/submit', json={})
    assert response.status_code == 400


# ---------------------------------------------------------------- unit: resolve_ai_pass_mode


def test_resolve_ai_pass_mode():
    """Bridge + enabled → skip; selain itu thread (termasuk disabled — thread sendiri yang me-skip)."""
    from backend.services.ai.mark_pass import resolve_ai_pass_mode

    assert resolve_ai_pass_mode({'enabled': True, 'provider': 'ollama'}) == 'skip'
    assert resolve_ai_pass_mode({'enabled': True, 'provider': 'lmstudio'}) == 'skip'
    assert resolve_ai_pass_mode({'enabled': True, 'provider': 'zai'}) == 'thread'
    assert resolve_ai_pass_mode({'enabled': True, 'provider': 'custom'}) == 'thread'
    assert resolve_ai_pass_mode({'enabled': False, 'provider': 'ollama'}) == 'thread'
    assert resolve_ai_pass_mode({}) == 'thread'


# ------------------------------------------------- Fase 3: review queue endpoint


def _insert_pending(ai_engine, txn_id, confidence, status='pending', description='TRSF GOJEK'):
    with ai_engine.begin() as conn:
        conn.execute(text(
            'INSERT INTO transactions (id, txn_date, description, amount, db_cr, bank_code, '
            'ai_suggested_mark_id, ai_confidence, ai_source, ai_status) VALUES '
            '(:id, :d, :desc, 50000, :dbcr, :bank, :mark, :conf, :source, :status)'
        ), {
            'id': txn_id, 'd': '2026-01-15', 'desc': description,
            'dbcr': 'CR', 'bank': 'BCA', 'mark': 'mark-beban',
            'conf': confidence, 'source': 'llm', 'status': status,
        })


def test_review_queue_menampilkan_pending_di_bawah_threshold(ai_client, ai_engine):
    _insert_mark(ai_engine)
    _insert_pending(ai_engine, 'txn-low', 0.55)     # di bawah → masuk queue
    _insert_pending(ai_engine, 'txn-mid', 0.75)     # di bawah → masuk
    _insert_pending(ai_engine, 'txn-high', 0.95)    # di atas threshold → tidak
    _insert_pending(ai_engine, 'txn-done', 0.55, status='accepted')  # sudah diputus → tidak

    response = ai_client.get('/api/transactions/ai-review-queue')
    assert response.status_code == 200
    data = response.get_json()
    ids = [item['id'] for item in data['items']]
    assert 'txn-low' in ids
    assert 'txn-mid' in ids
    assert 'txn-high' not in ids
    assert 'txn-done' not in ids
    assert data['total'] == 2
    assert data['threshold'] == pytest.approx(0.9)


def test_review_queue_threshold_bisa_dioverride(ai_client, ai_engine):
    _insert_mark(ai_engine)
    _insert_pending(ai_engine, 'txn-low', 0.55)
    _insert_pending(ai_engine, 'txn-mid', 0.75)

    response = ai_client.get('/api/transactions/ai-review-queue?threshold=0.6')
    data = response.get_json()
    ids = [item['id'] for item in data['items']]
    assert 'txn-low' in ids
    assert 'txn-mid' not in ids


def test_review_queue_tanpa_ai_columns_tidak_error(ai_client, ai_engine):
    """Skema lama (belum migrasi) → queue kosong, bukan 500."""
    with ai_engine.begin() as conn:
        conn.execute(text('DROP TABLE transactions'))
        conn.execute(text('''CREATE TABLE transactions (
            id TEXT PRIMARY KEY, txn_date TEXT, description TEXT,
            amount REAL, db_cr TEXT, bank_code TEXT, mark_id TEXT
        )'''))
    response = ai_client.get('/api/transactions/ai-review-queue')
    assert response.status_code == 200
    assert response.get_json()['items'] == []


# ---------------------------------------------------------------- test-connection


def test_ai_test_connection_pakai_kunci_vault_meski_base_url_dikirim(ai_client, ai_engine, monkeypatch):
    """Kunci vault tetap dipakai walau base_url dikirim eksplisit (frontend tak pernah mengirim api_key)."""
    from backend.services.ai import llm_client

    # seed ai_api_key + provider/base_url tersimpan (pola sama dgn test_settings_expose_bridge_flag)
    with ai_engine.begin() as conn:
        conn.execute(text('DELETE FROM app_settings'))
        conn.execute(text(
            "INSERT INTO app_settings (setting_key, setting_value) VALUES "
            "('ai_api_key', 'k-vault'), ('ai_provider', 'zai'), "
            "('ai_base_url', 'https://api.z.ai/api/paas/v4')"
        ))

    captured = {}

    def fake_list_models(base_url, timeout=llm_client.LIST_MODELS_TIMEOUT, api_key=None):
        captured.update(base_url=base_url, api_key=api_key)
        return ['m1']

    monkeypatch.setattr(llm_client, 'list_models', fake_list_models)

    resp = ai_client.post('/api/ai/test-connection', json={
        'base_url': 'https://api.z.ai/api/paas/v4', 'model': 'glm-4',
    })
    assert resp.status_code == 200
    assert captured['api_key'] == 'k-vault'
    assert captured['base_url'] == 'https://api.z.ai/api/paas/v4'
