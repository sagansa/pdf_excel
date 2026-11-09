# Browser-Bridge AI Lokal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Untuk provider AI lokal (LM Studio/Ollama), panggilan LLM dipindahkan dari backend (Docker/VPS) ke browser user — menyelesaikan `[Errno 111] Connection refused` saat production memanggil `localhost:11434`.

**Architecture:** Backend tetap memiliki seluruh logika (indeks riwayat, rule match, prompt few-shot, parsing, penyimpanan). Endpoint `ai-suggest` dipecah jadi `prepare` (rule + prompt tanpa LLM) dan `submit` (parse jawaban mentah dari browser). Provider z.ai/custom tetap memakai endpoint lama server-side. Pass AI latar belakang setelah konversi PDF dilewati untuk provider lokal, diganti header + banner di frontend.

**Tech Stack:** Flask + raw SQL `text()` (stdlib urllib untuk LLM server-side), pytest + SQLite in-memory, Vue 3 + Pinia, `fetch` native browser (tanpa dependency baru).

**Spec:** `docs/superpowers/specs/2026-11-09-browser-bridge-local-ai-design.md`

## Global Constraints

- Tidak ada dependency runtime baru — backend stdlib (`urllib` sudah ada), frontend `fetch` native.
- Tidak ada migrasi DB — kolom `ai_*` sudah ada (migrasi 072).
- Perilaku provider `zai` dan `custom` TIDAK berubah sama sekali (endpoint lama + thread PDF utuh).
- `ai_api_key` (z.ai) tidak pernah dikirim ke browser; prompt bridge tidak menyertakan api_key.
- Browser tidak dipercaya: `submit` memvalidasi `mark_id` terhadap kandidat dari DB; `raw` dipotong maksimal 64.000 karakter (`MAX_BRIDGE_RAW_LENGTH = 64000`).
- Semua pesan user-facing berbahasa Indonesia, mengikuti gaya pesan AI yang ada.
- Sumber kebenaran respons prepare/submit: `pending` = prompt `{id, model, messages, temperature: 0.1, max_tokens: 800}`; agregat submit = shape endpoint lama (`results`, `suggested_count`, `auto_applied_count`, `skipped_count`, `failed_count`, `message`).
- Test backend mengikuti fixture pola `tests/test_ai_bp.py` (`ai_engine`, `ai_app`, `ai_client`, `_insert_mark`, `_insert_transaction`, `_enable_ai`).

---

### Task 1: Flag `bridge` di `get_ai_settings`

**Files:**
- Modify: `admin_backend/backend/services/ai/llm_client.py` (fungsi `get_ai_settings`, blok return ~baris 176-186)
- Test: `admin_backend/tests/test_ai_bp.py`

**Interfaces:**
- Produces: `get_ai_settings(conn)` kini mengembalikan dict dengan field baru `bridge: bool` (`True` untuk provider `lmstudio`/`ollama`). Semua task lain membaca `settings['bridge']`.
- Consumes: `ALLOWED_PROVIDERS` (sudah ada).

- [ ] **Step 1: Tulis test gagal**

Tambahkan di akhir `tests/test_ai_bp.py`:

```python
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
```

- [ ] **Step 2: Jalankan test, verifikasi gagal**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py::test_settings_expose_bridge_flag -v`
Expected: FAIL — `KeyError: 'bridge'`

- [ ] **Step 3: Implementasi minimal**

Di `llm_client.py`, tambahkan konstanta setelah `ALLOWED_PROVIDERS`:

```python
BRIDGE_PROVIDERS = {'lmstudio', 'ollama'}
```

Di blok return `get_ai_settings` (sebelum `'api_key_set'`), tambahkan:

```python
        'bridge': provider in BRIDGE_PROVIDERS,
```

- [ ] **Step 4: Jalankan test, verifikasi lulus**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py::test_settings_expose_bridge_flag -v`
Expected: PASS

- [ ] **Step 5: Regresi penuh modul AI**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py -v`
Expected: semua PASS (field baru bersifat aditif).

- [ ] **Step 6: Commit**

```bash
git add admin_backend/backend/services/ai/llm_client.py admin_backend/tests/test_ai_bp.py
git commit -m "feat: flag bridge di settings AI — penanda provider lokal (lmstudio/ollama)"
```

---

### Task 2: Refactor `resolve_transaction_rules` + `execute_suggestion_prompt`

**Files:**
- Modify: `admin_backend/backend/services/ai/mark_suggester.py` (fungsi `process_transaction` ~baris 719-801; hapus `suggest_for_transaction` ~baris 563-585)
- Test: `admin_backend/tests/test_ai_bp.py`

**Interfaces:**
- Produces:
  - `resolve_transaction_rules(conn, txn_id, config, history_index=None, candidates_by_direction=None)` → `{'kind': 'done', 'result': {...}}` atau `{'kind': 'llm', 'txn': dict, 'candidates': list, 'prompt': {'id': str, 'model': str, 'messages': list, 'temperature': 0.1, 'max_tokens': 800}}`
  - `execute_suggestion_prompt(txn, candidates, prompt, config)` → dict saran tervalidasi (raise `LLMConnectionError`/`ValueError`)
- Consumes: `get_transaction`, `ensure_markable`, `load_candidate_marks`, `build_history_context`, `match_history_rule`, `match_amount_disambiguated_rule`, `pick_history_examples`, `summarize_recurring_marks`, `build_messages`, `parse_suggestion_response`, `store_suggestion` (semua sudah ada di modul yang sama).
- Catatan: `process_transaction` tetap ada dengan signature & hasil yang sama persis (dipakai endpoint lama + thread PDF). `suggest_for_transaction` DIHAPUS — hanya dipanggil `process_transaction` (tidak ada pemanggil lain di repo, sudah diverifikasi grep).

- [ ] **Step 1: Tulis test gagal**

Tambahkan di `tests/test_ai_bp.py` (test unit langsung, tanpa HTTP — memakai fixture `ai_engine` yang sudah ada):

```python
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
```

- [ ] **Step 2: Jalankan test, verifikasi gagal**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py::test_resolve_rules_returns_llm_prompt_without_calling_llm tests/test_ai_bp.py::test_resolve_rules_rule_match_stores_and_finishes -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'resolve_transaction_rules'`

- [ ] **Step 3: Implementasi refactor**

Di `mark_suggester.py`:

**3a.** Hapus fungsi `suggest_for_transaction` (baris ~563-585, mulai `def suggest_for_transaction` sampai sebelum `def ensure_ai_columns`).

**3b.** Ganti rentang `def process_transaction` sampai sebelum `def bulk_decision` dengan **ketiga fungsi** berikut (`resolve_transaction_rules`, `execute_suggestion_prompt`, `process_transaction`):

```python
def resolve_transaction_rules(conn, txn_id, config, history_index=None, candidates_by_direction=None):
    """Tahap TANPA LLM dari kaskade suggest: ambil transaksi, guard markable,
    kandidat, rule riwayat, rule disambiguasi nominal.

    Dipakai bersama oleh process_transaction (endpoint lama + thread PDF untuk
    provider server-side) dan endpoint bridge prepare. Rule yang cocok tetap
    langsung di-store di sini (perilaku instan yang sudah ada).

    Balikan:
      {'kind': 'done', 'result': {...}}  — selesai tanpa LLM (suggested|auto_applied|skipped)
      {'kind': 'llm', 'txn': ..., 'candidates': [...],
       'prompt': {'id', 'model', 'messages', 'temperature', 'max_tokens'}}
    """
    if candidates_by_direction is None:
        candidates_by_direction = {}

    txn = get_transaction(conn, txn_id)
    if txn is None:
        return {'kind': 'done', 'result': {
            'id': txn_id, 'status': 'skipped', 'reason': 'Transaksi tidak ditemukan'}}
    try:
        ensure_markable(conn, txn_id)
    except BadRequestError as exc:
        return {'kind': 'done', 'result': {
            'id': txn_id, 'status': 'skipped', 'reason': exc.message}}

    direction = _normalize_direction(txn.get('db_cr'))
    if direction not in candidates_by_direction:
        candidates_by_direction[direction] = load_candidate_marks(conn, direction)
    candidates = candidates_by_direction[direction]
    if not candidates:
        return {'kind': 'done', 'result': {
            'id': txn_id, 'status': 'skipped', 'reason': 'Belum ada mark yang tersedia'}}

    # Analisis riwayat marking user: kecocokan persis + mirip (fuzzy).
    context = build_history_context(history_index or [], txn, direction, txn.get('company_id'))

    # Lapis 1: pola dari riwayat user sendiri (instan, tanpa LLM).
    rule = match_history_rule(context, candidates)
    if rule:
        threshold = config.get('auto_apply_threshold')
        if threshold is None:
            threshold = llm_client.DEFAULT_AUTO_APPLY_THRESHOLD
        auto = bool(config.get('auto_apply')) and rule['confidence'] >= float(threshold)
        store_suggestion(conn, txn_id, rule, source='rule', auto_apply=auto)
        result = {
            'id': txn_id,
            'status': 'auto_applied' if auto else 'suggested',
            'ai_suggested_mark_id': rule['mark_id'],
            'mark_label': rule['mark_label'],
            'ai_confidence': rule['confidence'],
            'ai_reason': rule.get('reason'),
            'ai_source': 'rule',
        }
        if auto:
            result['auto_applied'] = True
        return {'kind': 'done', 'result': result}

    # Lapis 1c: deskripsi identik lintas mark, nominal membedakan → deterministik.
    amount_rule = match_amount_disambiguated_rule(context, txn, candidates)
    if amount_rule:
        store_suggestion(conn, txn_id, amount_rule, source='rule', auto_apply=False)
        return {'kind': 'done', 'result': {
            'id': txn_id,
            'status': 'suggested',
            'ai_suggested_mark_id': amount_rule['mark_id'],
            'mark_label': amount_rule['mark_label'],
            'ai_confidence': amount_rule['confidence'],
            'ai_reason': amount_rule.get('reason'),
            'ai_source': 'rule',
        }}

    # Tahap LLM: prompt siap pakai (few-shot riwayat + mark berulang).
    examples = pick_history_examples(context, history_index or [], txn, direction, txn.get('company_id'))
    recurring_marks = summarize_recurring_marks(context, txn_amount=_safe_amount(txn))
    messages = build_messages(txn, candidates, examples=examples, recurring_marks=recurring_marks)
    return {
        'kind': 'llm',
        'txn': txn,
        'candidates': candidates,
        'prompt': {
            'id': txn_id,
            'model': config.get('model'),
            'messages': messages,
            'temperature': 0.1,
            'max_tokens': 800,  # ruang untuk model reasoning sampai ke JSON jawaban
        },
    }


def execute_suggestion_prompt(txn, candidates, prompt, config):
    """Panggil LLM untuk satu prompt hasil resolve_transaction_rules.

    Satu retry kegagalan koneksi (model cold-load / server sibuk); kegagalan
    parsing JSON tidak diulang. Raise LLMConnectionError / ValueError.
    """
    kwargs = dict(
        base_url=config.get('base_url'),
        model=prompt.get('model') or config.get('model'),
        messages=prompt['messages'],
        temperature=prompt.get('temperature', 0.1),
        timeout=config.get('timeout') or llm_client.DEFAULT_TIMEOUT,
        max_tokens=prompt.get('max_tokens', 800),
        api_key=config.get('api_key') or None,
    )
    try:
        raw = llm_client.chat_completion(**kwargs)
    except llm_client.LLMConnectionError:
        time.sleep(2)
        raw = llm_client.chat_completion(**kwargs)
    return parse_suggestion_response(raw, candidates)


def process_transaction(conn, txn_id, config, history_index=None, candidates_by_direction=None):
    """Kaskade lengkap untuk satu transaksi: rule riwayat → (auto-apply) → LLM few-shot.

    Dipakai bersama oleh endpoint ai-suggest dan pass latar belakang saat konversi.
    Balikan dict result: {id, status: suggested|auto_applied|skipped|failed, ...}.
    """
    resolved = resolve_transaction_rules(
        conn, txn_id, config,
        history_index=history_index,
        candidates_by_direction=candidates_by_direction,
    )
    if resolved['kind'] == 'done':
        return resolved['result']

    prompt = resolved['prompt']
    try:
        suggestion = execute_suggestion_prompt(
            resolved['txn'], resolved['candidates'], prompt, config,
        )
    except llm_client.LLMConnectionError as exc:
        return {'id': txn_id, 'status': 'failed', 'error': str(exc)}
    except ValueError as exc:
        return {'id': txn_id, 'status': 'failed', 'error': str(exc)}

    store_suggestion(conn, txn_id, suggestion, source='llm')
    return {
        'id': txn_id,
        'status': 'suggested',
        'ai_suggested_mark_id': suggestion['mark_id'],
        'mark_label': suggestion['mark_label'],
        'ai_confidence': suggestion['confidence'],
        'ai_reason': suggestion.get('reason'),
        'ai_source': 'llm',
    }
```

- [ ] **Step 4: Jalankan test baru + regresi penuh**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py -v`
Expected: PASS semua — termasuk test lama `test_suggest_stores_pending_and_keeps_mark_id`, `test_suggest_prefers_history_rule_without_llm`, `test_llm_prompt_includes_history_examples`, `test_rule_auto_applies_when_enabled` (semua menembus path yang sama via endpoint lama).

- [ ] **Step 5: Commit**

```bash
git add admin_backend/backend/services/ai/mark_suggester.py admin_backend/tests/test_ai_bp.py
git commit -m "refactor: pisahkan tahap rule (resolve_transaction_rules) dari eksekusi LLM"
```

---

### Task 3: Endpoint `POST /api/transactions/ai-suggest/prepare`

**Files:**
- Modify: `admin_backend/backend/routes/transactions/ai_bp.py` (helper baru + route baru; refactor kecil `_validate_settings_payload` tidak disentuh)
- Test: `admin_backend/tests/test_ai_bp.py`

**Interfaces:**
- Consumes: `mark_suggester.resolve_transaction_rules` (Task 2), `llm_client.get_ai_settings` dengan `bridge` (Task 1).
- Produces: `POST /api/transactions/ai-suggest/prepare`, body `{transaction_ids: [...]}` → `{'results': [...], 'pending': [{id, model, messages, temperature, max_tokens}], 'message': str}`. Error codes sama dengan endpoint lama: `ai_disabled`, `ai_model_missing`. Validasi id identik (dedup, maks `MAX_SUGGEST_BATCH` = 15).
- `pending[i]` TIDAK menyertakan `api_key`.

- [ ] **Step 1: Tulis test gagal**

Tambahkan di `tests/test_ai_bp.py`:

```python
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
```

- [ ] **Step 2: Jalankan test, verifikasi gagal**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py::test_prepare_resolves_rules_and_returns_pending tests/test_ai_bp.py::test_prepare_validates_and_guards -v`
Expected: FAIL — 404 (route belum ada)

- [ ] **Step 3: Implementasi**

Di `ai_bp.py`, tambahkan helper `_parse_txn_ids` dan refactor endpoint lama `ai_suggest_marks` untuk memakainya, lalu tambahkan route prepare. Ganti blok validasi di `ai_suggest_marks` (baris 117-127):

```python
def _parse_txn_ids(data):
    """Validasi transaction_ids body: daftar string non-kosong, dedup, maks batch."""
    raw_ids = data.get('transaction_ids')
    if not isinstance(raw_ids, list) or not raw_ids:
        raise BadRequestError('transaction_ids wajib berupa daftar id transaksi.')
    txn_ids = []
    for value in raw_ids:
        txn_id = str(value or '').strip()
        if txn_id and txn_id not in txn_ids:
            txn_ids.append(txn_id)
    if not txn_ids:
        raise BadRequestError('transaction_ids tidak berisi id yang valid.')
    if len(txn_ids) > MAX_SUGGEST_BATCH:
        raise BadRequestError(
            f'Maksimal {MAX_SUGGEST_BATCH} transaksi per permintaan. '
            'Kirim dalam beberapa batch kecil.'
        )
    return txn_ids
```

Di `ai_suggest_marks` ganti baris 117-127 menjadi `txn_ids = _parse_txn_ids(data)`.

Tambahkan route baru SETELAH `ai_suggest_marks` (sebelum `ai_decision_bulk`):

```python
@ai_bp.route('/api/transactions/ai-suggest/prepare', methods=['POST'])
def ai_suggest_prepare():
    """Tahap bridge 1/2: kaskade rule TANPA LLM.

    Rule match langsung disimpan (instan & deterministik); sisanya dikembalikan
    sebagai prompt siap pakai untuk dipanggilkan ke server AI lokal oleh browser.
    """
    txn_ids = _parse_txn_ids(request.json or {})
    engine = require_db_engine()

    results, pending = [], []
    with engine.begin() as conn:
        mark_suggester.ensure_ai_columns(conn)
        config = llm_client.get_ai_settings(conn)
        if not config['enabled']:
            raise BadRequestError('Fitur AI belum diaktifkan di pengaturan.', code='ai_disabled')
        if not config['model']:
            raise BadRequestError('Model AI belum diatur di pengaturan.', code='ai_model_missing')

        history_index = mark_suggester.build_history_index(conn)
        candidates_by_direction = {}
        for txn_id in txn_ids:
            resolved = mark_suggester.resolve_transaction_rules(
                conn, txn_id, config,
                history_index=history_index,
                candidates_by_direction=candidates_by_direction,
            )
            if resolved['kind'] == 'done':
                results.append(resolved['result'])
            else:
                pending.append(resolved['prompt'])  # tanpa api_key — provider lokal

    return jsonify({
        'results': results,
        'pending': pending,
        'message': (
            f'{len(results)} selesai via aturan riwayat, '
            f'{len(pending)} menunggu jawaban server AI lokal.'
        ),
    })
```

- [ ] **Step 4: Jalankan test**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py -v`
Expected: PASS semua (endpoint lama tetap hijau — regresi).

- [ ] **Step 5: Commit**

```bash
git add admin_backend/backend/routes/transactions/ai_bp.py admin_backend/tests/test_ai_bp.py
git commit -m "feat: endpoint ai-suggest/prepare — kaskade rule tanpa LLM untuk bridge browser"
```

---

### Task 4: `parse_bridge_submission` + endpoint `POST /api/transactions/ai-suggest/submit`

**Files:**
- Modify: `admin_backend/backend/services/ai/mark_suggester.py` (fungsi baru setelah `process_transaction`)
- Modify: `admin_backend/backend/routes/transactions/ai_bp.py` (route baru setelah prepare)
- Test: `admin_backend/tests/test_ai_bp.py`

**Interfaces:**
- Consumes: `parse_suggestion_response`, `get_transaction`, `ensure_markable`, `load_candidate_marks`, `store_suggestion`, `_normalize_direction` (semua sudah ada di mark_suggester).
- Produces:
  - `mark_suggester.MAX_BRIDGE_RAW_LENGTH = 64000`
  - `mark_suggester.parse_bridge_submission(conn, txn_id, raw)` → result dict `{id, status: suggested|skipped|failed, ...}` — status `suggested` TIDAK pernah `auto_applied` (paritas: saran LLM selalu menunggu review).
  - `POST /api/transactions/ai-suggest/submit`, body `{items: [{id, raw?} | {id, error?}]}` → shape agregat endpoint lama.

- [ ] **Step 1: Tulis test gagal**

Tambahkan di `tests/test_ai_bp.py`:

```python
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
```

- [ ] **Step 2: Jalankan test, verifikasi gagal**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py::test_submit_stores_valid_raw tests/test_ai_bp.py::test_submit_rejects_bad_raw_and_unknown_ids tests/test_ai_bp.py::test_submit_validates_mark_against_db_candidates tests/test_ai_bp.py::test_submit_rejects_bad_body -v`
Expected: FAIL — 404 (route belum ada)

- [ ] **Step 3: Implementasi**

**3a.** Di `mark_suggester.py`, tambahkan konstanta di dekat `MAX_REASON_LENGTH`:

```python
MAX_BRIDGE_RAW_LENGTH = 64000  # jawaban mentah dari browser dipotong defensif
```

Tambahkan fungsi baru SETELAH `process_transaction` (sebelum `def bulk_decision`):

```python
def parse_bridge_submission(conn, txn_id, raw):
    """Validasi & simpan jawaban LLM mentah dari browser (bridge) untuk satu transaksi.

    Browser tidak dipercaya: transaksi, guard markable, dan kandidat diambil ulang
    dari DB; raw dipotong; parsing memvalidasi mark_id terhadap kandidat DB.
    Balikan result dict dengan status suggested|skipped|failed. Saran LLM tidak
    pernah auto-apply — selalu menunggu review (paritas endpoint lama).
    """
    txn = get_transaction(conn, txn_id)
    if txn is None:
        return {'id': txn_id, 'status': 'skipped', 'reason': 'Transaksi tidak ditemukan'}
    try:
        ensure_markable(conn, txn_id)
    except BadRequestError as exc:
        return {'id': txn_id, 'status': 'skipped', 'reason': exc.message}

    direction = _normalize_direction(txn.get('db_cr'))
    candidates = load_candidate_marks(conn, direction)
    if not candidates:
        return {'id': txn_id, 'status': 'skipped', 'reason': 'Belum ada mark yang tersedia'}

    raw = str(raw or '')[:MAX_BRIDGE_RAW_LENGTH]
    try:
        suggestion = parse_suggestion_response(raw, candidates)
    except ValueError as exc:
        return {'id': txn_id, 'status': 'failed', 'error': str(exc)}

    store_suggestion(conn, txn_id, suggestion, source='llm')
    return {
        'id': txn_id,
        'status': 'suggested',
        'ai_suggested_mark_id': suggestion['mark_id'],
        'mark_label': suggestion['mark_label'],
        'ai_confidence': suggestion['confidence'],
        'ai_reason': suggestion.get('reason'),
        'ai_source': 'llm',
    }
```

**3b.** Di `ai_bp.py`, tambahkan route SETELAH `ai_suggest_prepare`:

```python
@ai_bp.route('/api/transactions/ai-suggest/submit', methods=['POST'])
def ai_suggest_submit():
    """Tahap bridge 2/2: parse & simpan jawaban mentah server AI lokal.

    Browser mengirim jawaban mentah (atau error per item); server memvalidasi
    terhadap kandidat DB. Shape agregat identik dengan endpoint lama.
    """
    data = request.json or {}
    items = data.get('items')
    if not isinstance(items, list) or not items:
        raise BadRequestError('items wajib berupa daftar {id, raw|error}.')

    engine = require_db_engine()
    if len(items) > MAX_SUGGEST_BATCH:
        raise BadRequestError(
            f'Maksimal {MAX_SUGGEST_BATCH} transaksi per permintaan. '
            'Kirim dalam beberapa batch kecil.'
        )
    results = []
    with engine.begin() as conn:
        mark_suggester.ensure_ai_columns(conn)
        for item in items[:MAX_SUGGEST_BATCH]:
            if not isinstance(item, dict):
                raise BadRequestError('Setiap item wajib objek {id, raw|error}.')
            txn_id = str(item.get('id') or '').strip()
            if not txn_id:
                raise BadRequestError('Setiap item wajib memiliki id transaksi.')
            error = item.get('error')
            if error:
                results.append({'id': txn_id, 'status': 'failed', 'error': str(error)[:500]})
                continue
            results.append(mark_suggester.parse_bridge_submission(conn, txn_id, item.get('raw')))

    suggested_count = sum(1 for r in results if r['status'] == 'suggested')
    auto_applied_count = sum(1 for r in results if r['status'] == 'auto_applied')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    failed_count = sum(1 for r in results if r['status'] == 'failed')
    return jsonify({
        'results': results,
        'suggested_count': suggested_count,
        'auto_applied_count': auto_applied_count,
        'skipped_count': skipped_count,
        'failed_count': failed_count,
        'message': (
            f'{suggested_count} saran AI menunggu review, '
            f'{failed_count} gagal.'
        ),
    })
```

- [ ] **Step 4: Jalankan test**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py -v`
Expected: PASS semua.

- [ ] **Step 5: Commit**

```bash
git add admin_backend/backend/services/ai/mark_suggester.py admin_backend/backend/routes/transactions/ai_bp.py admin_backend/tests/test_ai_bp.py
git commit -m "feat: endpoint ai-suggest/submit — validasi jawaban bridge terhadap kandidat DB"
```

---

### Task 5: Skip pass PDF untuk provider lokal (`resolve_ai_pass_mode` + header)

**Files:**
- Modify: `admin_backend/backend/services/ai/mark_pass.py` (fungsi baru)
- Modify: `admin_backend/backend/routes/uploads/pdf_bp.py:303-312` (blok queue AI)
- Test: `admin_backend/tests/test_ai_bp.py` (unit untuk resolver; jalur PDF diverifikasi manual — tidak ada test pdf_bp existing, parsing PDF terlalu berat untuk fixture)

**Interfaces:**
- Consumes: `llm_client.get_ai_settings(conn)` dengan field `bridge` (Task 1); `backend.db.session.get_db_engine` (sudah ada).
- Produces:
  - `mark_pass.BRIDGE_PASS_ID_LIMIT = 100`
  - `mark_pass.resolve_ai_pass_mode(config)` → `'skip'` (enabled & provider bridge) atau `'thread'` (selain itu — thread sendiri me-skip bila AI disabled, paritas `mark_pass.py:50-55`).
  - Header response convert: `X-AI-Pass: queued` (thread dijadwalkan) | `skipped-local` (bridge, tidak dijadwalkan) | `off` (disabled/kegagalan — tanpa perubahan perilaku). `X-AI-Pass-Count` selalu ada untuk queued & skipped-local. Header `X-AI-Pass-Ids` (id dipisah koma) hanya saat skipped-local DAN jumlah id ≤ `BRIDGE_PASS_ID_LIMIT` — guard terhadap batas ukuran header.

- [ ] **Step 1: Tulis test gagal**

Tambahkan di `tests/test_ai_bp.py`:

```python
def test_resolve_ai_pass_mode():
    """Bridge + enabled → skip; selain itu thread (termasuk disabled — thread sendiri yang me-skip)."""
    from backend.services.ai.mark_pass import resolve_ai_pass_mode

    assert resolve_ai_pass_mode({'enabled': True, 'provider': 'ollama'}) == 'skip'
    assert resolve_ai_pass_mode({'enabled': True, 'provider': 'lmstudio'}) == 'skip'
    assert resolve_ai_pass_mode({'enabled': True, 'provider': 'zai'}) == 'thread'
    assert resolve_ai_pass_mode({'enabled': True, 'provider': 'custom'}) == 'thread'
    assert resolve_ai_pass_mode({'enabled': False, 'provider': 'ollama'}) == 'thread'
    assert resolve_ai_pass_mode({}) == 'thread'
```

- [ ] **Step 2: Jalankan test, verifikasi gagal**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py::test_resolve_ai_pass_mode -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_ai_pass_mode'`

- [ ] **Step 3: Implementasi resolver**

Di `mark_pass.py`, tambahkan setelah konstanta `logger`:

```python
# Provider lokal dijalankan dari BROWSER (laptop user) — server tidak dapat
# menjangkau localhost user, jadi pass latar belakang dilewati untuk mereka.
BRIDGE_PASS_ID_LIMIT = 100


def resolve_ai_pass_mode(config):
    """Putuskan jalur pass AI setelah konversi PDF berdasarkan settings AI.

    'skip'   — provider lokal (browser-bridge): server tidak dapat memanggil
               LLM di laptop user; pengguna menjalankan saran dari browser.
    'thread' — jalur lama: queue daemon thread (z.ai/custom; thread sendiri
               me-skip bila AI disabled atau model belum diatur).
    """
    if config.get('enabled') and config.get('provider') in llm_client.BRIDGE_PROVIDERS:
        return 'skip'
    return 'thread'
```

- [ ] **Step 4: Jalankan test**

Run: `cd admin_backend && venv/bin/pytest tests/test_ai_bp.py::test_resolve_ai_pass_mode -v`
Expected: PASS

- [ ] **Step 5: Wiring di pdf_bp**

Ganti blok `ai_pass_queued` di `pdf_bp.py` (baris 303-312):

```python
            # Pass AI setelah konversi: thread latar belakang untuk provider
            # server-side; provider lokal (laptop user) dilewati — dijalankan
            # dari browser. Kegagalan pass tidak pernah memengaruhi upload.
            ai_pass_queued = False
            ai_pass_mode = 'off'
            try:
                from backend.db.session import get_db_engine
                from backend.services.ai.llm_client import get_ai_settings
                from backend.services.ai.mark_pass import (
                    BRIDGE_PASS_ID_LIMIT,
                    queue_ai_mark_pass,
                    resolve_ai_pass_mode,
                )
                ai_engine, _ = get_db_engine()
                if ai_engine is not None:
                    with ai_engine.connect() as conn:
                        ai_config = get_ai_settings(conn)
                    ai_pass_mode = resolve_ai_pass_mode(ai_config)
                if ai_pass_mode == 'thread':
                    ai_pass_queued = queue_ai_mark_pass(inserted_ids)
            except Exception:
                app.logger.exception('Gagal menjadwalkan AI mark pass')

            response = send_file(output_path, as_attachment=True, download_name=f'{base_name}{file_extension}', mimetype=mimetype)
            if ai_pass_queued:
                response.headers['X-AI-Pass'] = 'queued'
                response.headers['X-AI-Pass-Count'] = str(len(inserted_ids))
            elif ai_pass_mode == 'skip':
                response.headers['X-AI-Pass'] = 'skipped-local'
                response.headers['X-AI-Pass-Count'] = str(len(inserted_ids))
                if len(inserted_ids) <= BRIDGE_PASS_ID_LIMIT:
                    response.headers['X-AI-Pass-Ids'] = ','.join(str(i) for i in inserted_ids)
```

- [ ] **Step 6: Regresi penuh backend + verifikasi manual cepat**

Run: `cd admin_backend && venv/bin/pytest tests/ -v`
Expected: PASS semua.

Verifikasi manual cepat (server dev + Ollama jalan): upload PDF kecil via halaman Converter dengan settings `ollama` enabled → response header `X-AI-Pass: skipped-local` ada (cek via DevTools Network); dengan settings `zai`/disabled → perilaku header tidak berubah dari sekarang.

- [ ] **Step 7: Commit**

```bash
git add admin_backend/backend/services/ai/mark_pass.py admin_backend/backend/routes/uploads/pdf_bp.py admin_backend/tests/test_ai_bp.py
git commit -m "feat: lewati pass AI latar belakang untuk provider lokal — header skipped-local + ids"
```

---

### Task 6: Modul relay frontend `localAiBridge.js`

**Files:**
- Create: `admin_frontend/src/services/localAiBridge.js`
- Pastikan direktori `admin_frontend/src/services/` dibuat bila belum ada.

**Interfaces:**
- Consumes: (dipanggil dari Task 7 & 8) — primitive `aiApi.prepareSuggest/submitSuggest` DITERIMA sebagai argumen pertama agar tidak ada import melingkar dengan `api/index.js`.
- Produces:
  - `runBridgeSuggest(aiApi, ids, settings)` → `Promise<{results: [...]}>` — results gabungan (rule + LLM), shape item identik dengan endpoint lama.
  - `listLocalModels(settings)` → `Promise<string[]>` — daftar model dari browser.
  - `describeBridgeNetworkError(provider, baseUrl)` → string pesan panduan (menyebut `window.location.origin`).
  - `fetchWithTimeout(url, options, timeoutMs)` — helper internal yang diekspor untuk pemakaian AiSettings.

- [ ] **Step 1: Tulis modul lengkap**

```js
/**
 * Bridge server AI lokal (LM Studio/Ollama) dari BROWSER user.
 *
 * Backend (Docker/VPS) tidak dapat menjangkau localhost di laptop user — hanya
 * browser-lah yang bisa. Modul ini menjembatani: mengambil prompt siap pakai
 * dari backend, memanggil server AI di laptop user, lalu menyerahkan jawaban
 * mentah ke backend untuk divalidasi & disimpan.
 *
 * Timeout & retry mengikuti paritas backend: 120s per panggilan, 1 retry pada
 * kegagalan jaringan (delay 2 detik, model cold-load/server sibuk).
 */

const DEFAULT_TIMEOUT_MS = 120000;
const LIST_MODELS_TIMEOUT_MS = 15000;
const RETRY_DELAY_MS = 2000;

export function describeBridgeNetworkError(provider, baseUrl) {
  const origin = window.location.origin;
  if (provider === 'ollama') {
    return `Tidak dapat menghubungi server AI di ${baseUrl} dari browser. `
      + `Pastikan Ollama berjalan di laptop Anda DAN mengizinkan origin ${origin} — `
      + `mis. jalankan: OLLAMA_ORIGINS="${origin},http://localhost:*" ollama serve`;
  }
  if (provider === 'lmstudio') {
    return `Tidak dapat menghubungi server AI di ${baseUrl} dari browser. `
      + `Pastikan LM Studio Server berjalan (tab Developer → Start Server) DAN opsi `
      + `"Enable CORS" aktif agar origin ${origin} diizinkan.`;
  }
  return `Tidak dapat menghubungi server AI di ${baseUrl} dari browser. `
    + `Pastikan server berjalan dan mengizinkan origin ${origin}.`;
}

export async function fetchWithTimeout(url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

const isNetworkFailure = (err) => err instanceof TypeError || err?.name === 'AbortError';

/** Satu panggilan /chat/completions ke laptop user; balikan teks isi pesan. */
export async function chatCompletionViaBridge(settings, prompt) {
  const base = String(settings?.base_url || '').replace(/\/+$/, '');
  const timeoutMs = (Number(settings?.timeout) || DEFAULT_TIMEOUT_MS / 1000) * 1000;
  const body = JSON.stringify({
    model: prompt.model,
    messages: prompt.messages,
    temperature: prompt.temperature ?? 0.1,
    max_tokens: prompt.max_tokens ?? 800,
    stream: false,
  });
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const response = await fetchWithTimeout(`${base}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body,
      }, timeoutMs);
      if (!response.ok) {
        const detail = (await response.text()).slice(0, 500);
        throw new Error(`Server AI menjawab HTTP ${response.status}: ${detail}`);
      }
      const data = await response.json();
      const message = data?.choices?.[0]?.message || {};
      // Model reasoning kadang menghabiskan token di field terpisah — paritas backend.
      const content = String(message.content || '').trim()
        || String(message.reasoning || '').trim();
      if (!content) throw new Error('Server AI mengembalikan isi pesan kosong.');
      return content;
    } catch (err) {
      if (attempt === 0 && isNetworkFailure(err)) {
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
        continue;
      }
      if (isNetworkFailure(err)) {
        throw new Error(describeBridgeNetworkError(settings?.provider, base));
      }
      throw err;
    }
  }
  throw new Error('Server AI tidak menjawab tepat waktu (timeout).');
}

/** Daftar model dari server AI lokal, langsung dari browser (timeout 15s). */
export async function listLocalModels(settings) {
  const base = String(settings?.base_url || '').replace(/\/+$/, '');
  let response;
  try {
    response = await fetchWithTimeout(
      `${base}/models`,
      { headers: { Accept: 'application/json' } },
      LIST_MODELS_TIMEOUT_MS,
    );
  } catch (err) {
    throw new Error(describeBridgeNetworkError(settings?.provider, base));
  }
  if (!response.ok) {
    throw new Error(`Server AI menjawab HTTP ${response.status}.`);
  }
  const data = await response.json();
  const items = Array.isArray(data) ? data : (data.data || []);
  return items
    .map((item) => (typeof item === 'string' ? item : String(item?.id || '')))
    .filter(Boolean);
}

/**
 * Alur suggest lengkap via bridge: prepare → panggil LLM lokal per prompt
 * (sekuensial, paritas loop server) → submit jawaban mentah.
 * Balikan {results} gabungan — shape item identik endpoint lama.
 */
export async function runBridgeSuggest(aiApi, ids, settings) {
  const { data: prep } = await aiApi.prepareSuggest(ids);
  const items = [];
  for (const prompt of prep.pending || []) {
    try {
      const raw = await chatCompletionViaBridge(settings, prompt);
      items.push({ id: prompt.id, raw });
    } catch (err) {
      items.push({ id: prompt.id, error: String(err?.message || err) });
    }
  }
  let llmResults = [];
  if (items.length > 0) {
    const { data } = await aiApi.submitSuggest(items);
    llmResults = data.results || [];
  }
  return { results: [...(prep.results || []), ...llmResults] };
}
```

- [ ] **Step 2: Build frontend**

Run: `cd admin_frontend && npx vite build 2>&1 | tail -5`
Expected: build sukses tanpa error sintaks.

- [ ] **Step 3: Commit**

```bash
git add admin_frontend/src/services/localAiBridge.js
git commit -m "feat: modul bridge server AI lokal dari browser (prepare→LLM lokal→submit)"
```

---

### Task 7: Dispatcher `aiApi.suggestMarks` + primitive prepare/submit

**Files:**
- Modify: `admin_frontend/src/api/index.js` (objek `aiApi`, baris ~556)
- Modify: `admin_frontend/src/stores/history.js` (2 call site `aiApi.suggestMarks`: baris ~734 dan ~769)

**Interfaces:**
- Consumes: `runBridgeSuggest` (Task 6); `settings.bridge` dari store cache (Task 1 — field sudah ikut respons GET /ai/settings).
- Produces: `aiApi.suggestMarks(transactionIds, settings = null)` — signature lama tetap kompatibel (settings opsional). `aiApi.prepareSuggest(ids)`, `aiApi.submitSuggest(items)`. Store action `aiSuggestSelected(ids = null)` — param opsional, default perilaku lama (pakai seleksi).

- [ ] **Step 1: Ubah `aiApi`**

Di `api/index.js`, tambahkan import di atas:

```js
import { runBridgeSuggest } from '../services/localAiBridge';
```

Ganti fungsi `suggestMarks` dalam `aiApi` dan tambahkan dua primitive (fungsi lain tidak diubah):

```js
  suggestMarks(transactionIds, settings = null) {
    // Provider lokal (lmstudio/ollama): LLM dipanggil dari BROWSER — backend
    // di Docker/VPS tidak dapat menjangkau localhost laptop user.
    if (settings?.bridge && settings.enabled) {
      return runBridgeSuggest(aiApi, transactionIds, settings)
        .then((data) => ({ data }));
    }
    return api.post('/transactions/ai-suggest', { transaction_ids: transactionIds });
  },
  prepareSuggest(transactionIds) {
    return api.post('/transactions/ai-suggest/prepare', { transaction_ids: transactionIds });
  },
  submitSuggest(items) {
    return api.post('/transactions/ai-suggest/submit', { items });
  },
```

- [ ] **Step 2: Teruskan settings dari store**

Di `stores/history.js` — fungsi `suggestMark` (~baris 734):

```js
            const { data } = await aiApi.suggestMarks([txnId], this.aiSettings);
```

Dan dalam `aiSuggestSelected` (~baris 769):

```js
                    const { data } = await aiApi.suggestMarks(chunk, this.aiSettings);
```

Kedua call site sudah memanggil `ensureAiSettings()` sebelumnya, jadi `this.aiSettings` selalu terisi (dengan fallback `{enabled:false}` yang berarti tetap memakai endpoint lama dan akan ditolak backend dengan `ai_disabled` — perilaku tersama).

- [ ] **Step 3: Param opsional `aiSuggestSelected`** (dipakai Task 9)

Di `stores/history.js`, ubah kepala fungsi:

```js
    async aiSuggestSelected(ids = null) {
        ids = ids || [...this.selectedTxnIds];
        if (ids.length === 0) return { suggested: 0, skipped: 0, failed: 0 };
```

(ganti dua baris lama yang membaca `const ids = [...this.selectedTxnIds];`). Baris lain dalam fungsi tidak berubah — `ids` yang dipakai loop chunk otomatis mengikuti nilai baru ini.

- [ ] **Step 4: Build + regresi sintaks**

Run: `cd admin_frontend && npx vite build 2>&1 | tail -5`
Expected: build sukses.

- [ ] **Step 5: Commit**

```bash
git add admin_frontend/src/api/index.js admin_frontend/src/stores/history.js
git commit -m "feat: suggestMarks dispatcher — provider lokal via bridge browser, lainnya endpoint lama"
```

---

### Task 8: AiSettings — tes koneksi & daftar model dari browser + panel panduan CORS

**Files:**
- Modify: `admin_frontend/src/components/settings/AiSettings.vue`

**Interfaces:**
- Consumes: `listLocalModels`, `describeBridgeNetworkError` (Task 6); `form.provider`.
- Produces: provider bridge → tes koneksi & preload daftar model berjalan dari browser; panel panduan CORS tampil hanya untuk provider bridge.

- [ ] **Step 1: Script changes**

Di `<script setup>` AiSettings.vue:

**1a.** Tambah import:

```js
import { listLocalModels } from '../../services/localAiBridge';
```

**1b.** Tambah computed setelah `needsApiKey`:

```js
// Provider lokal dipanggil langsung dari browser (bridge) — backend di VPS
// tidak dapat menjangkau localhost laptop user.
const isBridgeProvider = computed(() => ['lmstudio', 'ollama'].includes(form.provider));
const currentOrigin = window.location.origin;
```

**1c.** Di `onMounted`, ganti blok preload model (dari komentar "Muat daftar model milik provider aktif..." sampai akhir try-catch) dengan:

```js
  // Muat daftar model milik provider aktif di latar belakang (diam bila gagal)
  // supaya dropdown model langsung sesuai server yang dipilih.
  if (form.enabled && form.baseUrl) {
    try {
      if (isBridgeProvider.value) {
        const models = await listLocalModels({ base_url: form.baseUrl, provider: form.provider });
        modelOptions.value = models.map((id) => ({ id, label: id }));
      } else {
        const payload = { base_url: form.baseUrl, model: form.model };
        if (needsApiKey.value && apiKeySet.value && form.apiKey.trim()) payload.api_key = form.apiKey.trim();
        const { data } = await aiApi.testConnection(payload);
        modelOptions.value = (data.models || []).map((id) => ({ id, label: id }));
      }
    } catch (err) {
      // Diamkan: pengguna bisa memicu "Tes Koneksi" manual.
    }
  }
```

**1d.** Ganti isi `handleTestConnection` (setelah guard `baseUrl` kosong yang tetap) dengan:

```js
  isTesting.value = true;
  try {
    if (isBridgeProvider.value) {
      const models = await listLocalModels({ base_url: form.baseUrl, provider: form.provider });
      modelOptions.value = models.map((id) => ({ id, label: id }));
      let message = `Koneksi berhasil. ${models.length} model tersedia.`;
      if (form.model && !models.includes(form.model)) {
        message += ` Model "${form.model}" belum termuat di server.`;
      }
      testStatus.value = { ok: true, message };
      return;
    }
    const payload = { base_url: form.baseUrl, model: form.model };
    if (needsApiKey.value && apiKeyDirty.value && form.apiKey.trim()) {
      payload.api_key = form.apiKey.trim();
    }
    const { data } = await aiApi.testConnection(payload);
    modelOptions.value = (data.models || []).map((id) => ({ id, label: id }));
    let message = data.message || 'Koneksi berhasil.';
    if (form.model && !data.model_found) {
      message += ` Model "${form.model}" belum termuat di server.`;
    }
    testStatus.value = { ok: true, message };
  } catch (err) {
    const detail = err?.response?.data?.error || err?.message || 'Server AI tidak dapat dihubungi.';
    testStatus.value = { ok: false, message: detail };
    modelOptions.value = [];
  } finally {
    isTesting.value = false;
  }
```

- [ ] **Step 2: Template — panel panduan CORS**

Sisipkan blok berikut tepat SETELAH div peringatan provider cloud (`v-if="form.provider === 'zai'"` berakhir sebelum `div v-if="needsApiKey"`), yaitu di antara keduanya:

```html
        <!-- Provider lokal: LLM dipanggil dari browser user (bridge). Origin ini
             harus diizinkan oleh server AI di laptop user. -->
        <div
          v-if="isBridgeProvider"
          class="rounded-xl border border-sky-200 bg-sky-50 p-4 transition-colors dark:border-sky-900/50 dark:bg-sky-900/20"
        >
          <div class="flex gap-3">
            <i class="bi bi-pc-display text-sky-600 dark:text-sky-400"></i>
            <div class="text-xs leading-relaxed text-sky-800 dark:text-sky-200">
              <strong>Dijalankan dari browser Anda:</strong> server AI dihubungi langsung dari
              browser ini (origin <code class="font-mono">{{ currentOrigin }}</code>), bukan dari server
              aplikasi. Di laptop Anda, izinkan origin tersebut:
              <span v-if="form.provider === 'ollama'">
                jalankan Ollama dengan <code class="font-mono">OLLAMA_ORIGINS="{{ currentOrigin }},http://localhost:*"</code>.
              </span>
              <span v-else>
                di LM Studio tab Developer, aktifkan <strong>Enable CORS</strong>.
              </span>
            </div>
          </div>
        </div>
```

- [ ] **Step 3: Build**

Run: `cd admin_frontend && npx vite build 2>&1 | tail -5`
Expected: build sukses.

- [ ] **Step 4: Verifikasi manual (dev, Ollama jalan)**

Jalankan backend + frontend dev. Settings → pilih provider Ollama → panel biru panduan tampil → "Tes Koneksi" → daftar model terisi dari Ollama (cek DevTools Network: request ke `localhost:11434/v1/models` ber-origin browser, bukan via backend). Matikan Ollama → "Tes Koneksi" → pesan panduan dengan `OLLAMA_ORIGINS` muncul, UI tidak crash.

- [ ] **Step 5: Commit**

```bash
git add admin_frontend/src/components/settings/AiSettings.vue
git commit -m "feat: tes koneksi & daftar model AI lokal dari browser + panel panduan CORS"
```

---

### Task 9: Banner pasca-konversi PDF — "siap untuk saran AI"

**Files:**
- Modify: `admin_frontend/src/stores/converter.js` (`confirmSave`, ~baris 77-100; tambah state & action baru)
- Modify: `admin_frontend/src/views/ConverterView.vue` (~baris 133-141 blok successMessage; handler tombol)
- Modify: `admin_frontend/src/stores/history.js` — sudah selesai di Task 7 (`aiSuggestSelected(ids)`)

**Interfaces:**
- Consumes: header `X-AI-Pass: skipped-local`, `X-AI-Pass-Count`, `X-AI-Pass-Ids` (Task 5); `useHistoryStore().aiSuggestSelected(ids)` (Task 7); axios mengekspos header sebagai `response.headers['x-ai-pass']` (lowercase).
- Produces: `converterStore.aiPendingLocal = {count, ids} | null`; action `converterStore.runLocalAiPass()` → `Promise<summary|null>`.

- [ ] **Step 1: State & confirmSave**

Di `stores/converter.js`: state baru di dalam `state: () => ({ ... })` (tambahkan setelah `successMessage` yang ada):

```js
      // Pass AI lokal yang ditunda setelah konversi (provider AI lokal — dijalankan dari browser).
      aiPendingLocal: null,
```

Ganti blok pembacaan header dalam `confirmSave`:

```js
            // Header X-AI-Pass: hasil penjadwalan pass penandaan AI setelah konversi.
            // skipped-local = provider AI lokal: server tidak dapat memanggil LLM di
            // laptop user — saran dijalankan manual dari browser (banner + tombol).
            const aiHeader = response.headers?.['x-ai-pass'];
            const aiCount = Number(response.headers?.['x-ai-pass-count']) || 0;
            const aiIds = String(response.headers?.['x-ai-pass-ids'] || '')
              .split(',').map((id) => id.trim()).filter(Boolean);
            this.aiPendingLocal = aiHeader === 'skipped-local'
              ? { count: aiCount || aiIds.length, ids: aiIds }
              : null;
            this.successMessage = aiHeader === 'queued'
                ? `Conversion & DB Sync successful! AI sedang menandai ${aiCount ?? 'baru'} transaksi di latar belakang.`
                : aiHeader === 'skipped-local'
                    ? `Conversion & DB Sync successful! ${this.aiPendingLocal.count} transaksi baru siap untuk saran AI.`
                    : "Conversion & DB Sync successful!";
            return response.data;
```

Tambahkan action baru setelah `confirmSave`:

```js
    /** Jalankan saran AI (via bridge browser) untuk transaksi hasil konversi yang ditunda. */
    async runLocalAiPass() {
      const pending = this.aiPendingLocal;
      if (!pending || pending.ids.length === 0) return null;
      const { useHistoryStore } = await import('./history');
      const historyStore = useHistoryStore();
      const summary = await historyStore.aiSuggestSelected(pending.ids);
      this.aiPendingLocal = null;
      return summary;
    },
```

- [ ] **Step 2: Template banner di ConverterView**

Ganti blok `feedback-box--success` (baris 133-141) dengan:

```html
        <div
          v-if="converterStore.successMessage"
          class="feedback-box feedback-box--success rounded-2xl p-4 text-sm"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center">
              <i class="bi bi-check-circle-fill me-3 text-lg"></i>
              <span>{{ converterStore.successMessage }}</span>
            </div>
            <button
              v-if="converterStore.aiPendingLocal?.count"
              type="button"
              class="btn-primary shrink-0 rounded-xl px-4 py-2 text-xs font-bold inline-flex items-center gap-2"
              :disabled="historyStore.aiBulkBusy"
              @click="handleRunLocalAiPass"
            >
              <i v-if="historyStore.aiBulkBusy" class="bi bi-arrow-repeat animate-spin"></i>
              <i v-else class="bi bi-stars"></i>
              {{ historyStore.aiBulkBusy
                ? `Menandai... (${historyStore.aiBulkProgress.done}/${historyStore.aiBulkProgress.total})`
                : `Tandai ${converterStore.aiPendingLocal.count} transaksi dengan AI` }}
            </button>
          </div>
        </div>
```

- [ ] **Step 3: Handler di script ConverterView**

Tambahkan import store history di `<script setup>`:

```js
import { useConverterStore } from '../stores/converter';
import { useHistoryStore } from '../stores/history';
```

(sesuaikan bila import converter store sudah ada dengan bentuk lain — pertahankan yang ada, tambahkan yang belum).

Tambahkan const store history di dekat deklarasi `converterStore` yang ada:

```js
const historyStore = useHistoryStore();
```

Dan handler (di dekat handler lain, mis. setelah fungsi yang memanggil `confirmSave` ~baris 433):

```js
const handleRunLocalAiPass = async () => {
  try {
    const summary = await converterStore.runLocalAiPass();
    if (summary) {
      const ok = (summary.suggested || 0) + (summary.auto_applied || 0);
      const failed = summary.failed || 0;
      alert(`Saran AI selesai: ${ok} saran dibuat, ${failed} gagal.`);
    }
  } catch (e) {
    alert(`Gagal menjalankan saran AI: ${e.message}`);
  }
};
```

- [ ] **Step 4: Build**

Run: `cd admin_frontend && npx vite build 2>&1 | tail -5`
Expected: build sukses.

- [ ] **Step 5: Verifikasi manual (dev, Ollama jalan, settings provider ollama)**

Konversi PDF kecil → banner sukses memuat tombol "Tandai N transaksi dengan AI" → klik → spinner per transaksi → hasil saran muncul di History (ai_status pending). Ganti settings ke z.ai (mock tidak perlu — cukup verifikasi banner TIDAK tampil dan perilaku lama tetap).

- [ ] **Step 6: Commit**

```bash
git add admin_frontend/src/stores/converter.js admin_frontend/src/views/ConverterView.vue
git commit -m "feat: banner & tombol saran AI pasca-konversi untuk provider lokal"
```

---

### Task 10: Verifikasi E2E & checklist rilis

**Files:**
- Tidak ada perubahan kode — verifikasi menyeluruh + catatan dokumentasi.

**Interfaces:**
- Consumes: semua task sebelumnya.

- [ ] **Step 1: Regresi backend penuh**

Run: `cd admin_backend && venv/bin/pytest tests/ -v`
Expected: PASS semua.

- [ ] **Step 2: Build frontend rilis**

Run: `cd admin_frontend && npx vite build`
Expected: sukses tanpa warning error baru.

- [ ] **Step 3: Checklist manual dev (semua dari browser, Ollama jalan)**

1. History: pilih 1 transaksi tanpa riwayat → "Saran AI" → DevTools Network: `ai-suggest/prepare` → `localhost:11434/v1/chat/completions` (DARI browser) → `ai-suggest/submit`. Saran tampil pending.
2. History: transaksi dengan riwayat persis → saran instan TANPA panggilan chat/completions (hanya prepare).
3. History: batch multi-select (3-5) → progres per baris jalan, hasil agregat benar.
4. Ollama mati + suggest → toast error panduan (menyebut OLLAMA_ORIGINS + origin), item lain tidak crash; cek DB: transaksi tetap tanpa saran.
5. Settings Ollama: Tes Koneksi sukses + model list; panel panduan CORS tampil dengan origin benar.
6. Konversi PDF: banner + tombol "Tandai N transaksi" berfungsi; setelah selesai banner hilang.
7. Ganti provider z.ai dengan API key valid: suggest & tes koneksi tetap lewat backend (Network: request ke `/api/transactions/ai-suggest`, bukan bridge) — regresi path lama.

- [ ] **Step 4: Checklist E2E production (simulasi Docker + laptop user)**

1. Backend berjalan di Docker; akses UI dari laptop yang SAMA → tetap berfungsi (origin `http://localhost:*` diizinkan Ollama default... verifikasi; bila tidak, `OLLAMA_ORIGINS="http://localhost:5173"`).
2. Akses UI dari laptop LAIN yang menjalankan Ollama → `OLLAMA_ORIGINS` memuat origin production → tes koneksi + suggest sukses dari browser laptop itu.
3. Laptop tanpa Ollama → pesan panduan tampil, tidak ada error server di log backend.

- [ ] **Step 5: Commit final (bila ada perbaikan kecil hasil verifikasi)**

```bash
git add -A
git commit -m "chore: perbaikan kecil hasil verifikasi E2E browser-bridge"
```

---

## Self-Review (sudah dijalankan)

1. **Spec coverage**: §1 routing bridge → Task 1; §2 backend prepare/submit + refactor → Task 2-4; §3 frontend relay + dispatcher + settings UI → Task 6-8; §4 PDF skip + banner → Task 5 & 9; §5 error handling CORS → Task 6 (`describeBridgeNetworkError`) & 8 (panel); §6 keamanan → Task 4 (validasi DB + potong raw) & prompt tanpa api_key (Task 2-3); §7 testing → tiap task + Task 10; §8 batasan — tidak ada dependency/migrasi (semua task).
2. **Placeholder scan**: tidak ada TBD/TODO; semua langkah berisi kode lengkap atau perintah exact.
3. **Type consistency**: `resolve_transaction_rules` → `{kind, result|txn, candidates, prompt}` konsisten Task 2/3; `parse_bridge_submission` result shape konsisten Task 4; `runBridgeSuggest(aiApi, ids, settings)` → `{results}` konsisten Task 6/7; `aiSuggestSelected(ids = null)` konsisten Task 7/9; `aiPendingLocal = {count, ids}` konsisten Task 9.
4. **Deviasi kecil dari spec (dokumentasi sadar)**: spec §3b menyebut "komponen & store tidak berubah" — realitasnya store perlu 2 perubahan satu baris (meneruskan `this.aiSettings` ke dispatcher, param opsional `aiSuggestSelected(ids)` untuk banner konversi). Ini tetap sesuai semangat spec (komponen tak berubah); tercatat di Task 7 & 9.
