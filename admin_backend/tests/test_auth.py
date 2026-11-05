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
