import logging

from sqlalchemy import text


def _token_rows(engine, user_id):
    with engine.connect() as conn:
        return conn.execute(
            text('SELECT token_hash FROM password_reset_tokens WHERE user_id = :uid'),
            {'uid': user_id},
        ).fetchall()


def test_forgot_password_returns_generic_success_for_unknown_email(client):
    response = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})

    assert response.status_code == 200
    assert response.get_json() == {
        'ok': True,
        'message': 'If an account exists for that email, a reset link has been sent.',
    }


def test_forgot_password_creates_hashed_token_and_logs_link(client, make_user, engine, caplog):
    user_id = make_user(email='admin@example.com')

    with caplog.at_level(logging.WARNING, logger='backend.services.mailer'):
        response = client.post('/api/auth/forgot-password', json={'email': 'admin@example.com'})

    assert response.status_code == 200
    rows = _token_rows(engine, user_id)
    assert len(rows) == 1
    # Disimpan sebagai SHA-256 hex (64 char), bukan token mentah.
    assert len(rows[0][0]) == 64
    # Token mentah hanya muncul di link yang di-log (mode dev mailer).
    assert '/reset-password?token=' in caplog.text


def test_forgot_password_replaces_previous_tokens(client, make_user, engine):
    user_id = make_user(email='admin@example.com')
    client.post('/api/auth/forgot-password', json={'email': 'admin@example.com'})
    client.post('/api/auth/forgot-password', json={'email': 'ADMIN@example.com'})

    assert len(_token_rows(engine, user_id)) == 1


def test_forgot_password_ignores_inactive_user(client, make_user, engine):
    user_id = make_user(email='ghost@example.com', is_active=0)

    response = client.post('/api/auth/forgot-password', json={'email': 'ghost@example.com'})

    assert response.status_code == 200
    assert _token_rows(engine, user_id) == []


def test_forgot_password_rate_limited_after_three_requests(client):
    for _ in range(3):
        response = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})
        assert response.status_code == 200

    response = client.post('/api/auth/forgot-password', json={'email': 'nobody@example.com'})
    assert response.status_code == 429


def test_me_requires_authentication(client):
    response = client.get('/api/auth/me')
    assert response.status_code == 401
    assert response.get_json()['code'] == 'not_authenticated'


def test_login_with_email_succeeds(client, make_user):
    make_user(email='admin@example.com', password='password123')

    response = client.post('/api/auth/login', json={
        'email': 'admin@example.com', 'password': 'password123',
    })

    assert response.status_code == 200
    assert response.get_json()['user'] == {
        'id': 1, 'email': 'admin@example.com', 'display_name': 'Admin',
    }


def test_login_email_is_case_insensitive(client, make_user):
    make_user(email='admin@example.com', password='password123')

    response = client.post('/api/auth/login', json={
        'email': '  ADMIN@Example.COM ', 'password': 'password123',
    })

    assert response.status_code == 200


def test_login_wrong_password_rejected(client, make_user):
    make_user(email='admin@example.com', password='password123')

    response = client.post('/api/auth/login', json={
        'email': 'admin@example.com', 'password': 'wrongpassword',
    })

    assert response.status_code == 401
    assert response.get_json()['code'] == 'invalid_credentials'


def test_me_returns_email_after_login(client, make_user):
    make_user(email='admin@example.com', password='password123')
    client.post('/api/auth/login', json={
        'email': 'admin@example.com', 'password': 'password123',
    })

    response = client.get('/api/auth/me')

    assert response.status_code == 200
    assert response.get_json()['user']['email'] == 'admin@example.com'


def _reset_token_from_log(caplog):
    for line in caplog.text.splitlines():
        if '/reset-password?token=' in line:
            return line.rsplit('token=', 1)[1].strip()
    raise AssertionError('reset token not found in logs')


def _request_reset(client, caplog, email='admin@example.com'):
    import logging as _logging
    with caplog.at_level(_logging.WARNING, logger='backend.services.mailer'):
        response = client.post('/api/auth/forgot-password', json={'email': email})
    assert response.status_code == 200
    return _reset_token_from_log(caplog)


def test_reset_password_flow(client, make_user, caplog, engine):
    make_user(email='admin@example.com', password='oldpassword123')
    token = _request_reset(client, caplog)

    response = client.post('/api/auth/reset-password', json={
        'token': token, 'new_password': 'newpassword456',
    })

    assert response.status_code == 200
    # Password lama ditolak, yang baru diterima.
    old = client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'oldpassword123'})
    assert old.status_code == 401
    new = client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'newpassword456'})
    assert new.status_code == 200
    with engine.connect() as conn:
        remaining = conn.execute(
            text('SELECT COUNT(*) FROM password_reset_tokens WHERE user_id = :uid'),
            {'uid': 1},
        ).scalar_one()
    assert remaining == 0


def test_reset_token_is_single_use(client, make_user, caplog):
    make_user(email='admin@example.com', password='oldpassword123')
    token = _request_reset(client, caplog)
    first = client.post('/api/auth/reset-password', json={'token': token, 'new_password': 'newpassword456'})
    assert first.status_code == 200

    second = client.post('/api/auth/reset-password', json={'token': token, 'new_password': 'anotherpass789'})

    assert second.status_code == 400
    assert second.get_json()['code'] == 'invalid_token'


def test_reset_token_expired_is_rejected(client, make_user, engine):
    from datetime import datetime as _dt, timedelta as _td

    make_user(email='admin@example.com', password='oldpassword123')
    from backend.routes.auth_bp import _hash_token
    with engine.begin() as conn:
        conn.execute(
            text(
                'INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) '
                'VALUES (1, :th, :exp)'
            ),
            {'th': _hash_token('expired-token'), 'exp': _dt.now() - _td(minutes=1)},
        )

    response = client.post('/api/auth/reset-password', json={
        'token': 'expired-token', 'new_password': 'newpassword456',
    })

    assert response.status_code == 400
    assert response.get_json()['code'] == 'invalid_token'


def test_reset_password_too_short_rejected(client, make_user, caplog):
    make_user(email='admin@example.com', password='oldpassword123')
    token = _request_reset(client, caplog)

    response = client.post('/api/auth/reset-password', json={
        'token': token, 'new_password': 'short',
    })

    assert response.status_code == 400
    assert response.get_json()['code'] == 'password_too_short'


def test_reset_password_invalidates_other_sessions(app, client, make_user, caplog):
    make_user(email='admin@example.com', password='oldpassword123')
    client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': 'oldpassword123'})
    assert client.get('/api/auth/me').status_code == 200

    other = app.test_client()
    token = _request_reset(other, caplog)
    assert other.post('/api/auth/reset-password', json={
        'token': token, 'new_password': 'newpassword456',
    }).status_code == 200

    # Sesi lama (client pertama) harus mati.
    assert client.get('/api/auth/me').status_code == 401
