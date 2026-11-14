"""Unit test route_utils — header User-Agent pada fetch API remote.

UA default Python-urllib diblokir Cloudflare zona sagansa.id (error 1010)
sebelum request sampai ke aplikasi superadmin, jadi semua fetch remote wajib
mengirim User-Agent identifikasi aplikasi.
"""

from backend.routes import route_utils


class _FakeResp:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"data": []}'


def test_fetch_remote_json_kirim_user_agent(monkeypatch):
    captured = {}

    def _fake_urlopen(req, timeout=None):
        captured['ua'] = req.get_header('User-agent')
        captured['auth'] = req.get_header('Authorization')
        return _FakeResp()

    monkeypatch.setattr(route_utils.urlrequest, 'urlopen', _fake_urlopen)
    payload = route_utils._fetch_remote_json(
        'https://superadmin.sagansa.id/api/presences', 'tok-123')

    assert payload == {'data': []}
    assert captured['auth'] == 'Bearer tok-123'
    assert captured['ua'], 'User-Agent wajib di-set — UA default urllib diblokir Cloudflare'
    assert 'python-urllib' not in captured['ua'].lower()
