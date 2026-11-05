def test_me_requires_authentication(client):
    response = client.get('/api/auth/me')
    assert response.status_code == 401
    assert response.get_json()['code'] == 'not_authenticated'
