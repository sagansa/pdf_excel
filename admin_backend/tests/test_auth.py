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
