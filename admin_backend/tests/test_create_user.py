from scripts.create_user import is_valid_email, normalize_email


def test_normalize_email_trims_and_lowercases():
    assert normalize_email('  Admin@Example.COM  ') == 'admin@example.com'


def test_is_valid_email_accepts_normal_addresses():
    assert is_valid_email('admin@sagansa.com')
    assert is_valid_email('a.b+tag@sub.domain.co.id')


def test_is_valid_email_rejects_garbage():
    assert not is_valid_email('admin')
    assert not is_valid_email('admin@')
    assert not is_valid_email('admin@localhost')
    assert not is_valid_email('admin example.com')
    assert not is_valid_email('')
