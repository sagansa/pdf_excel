from backend.routes.rental.rental_queries import (
    build_filter_rent_transaction_ids_query,
    build_linkable_transactions_query,
)


def test_filter_rent_transaction_ids_query_uses_explicit_rental_marks_only():
    sql = str(build_filter_rent_transaction_ids_query())

    assert "COALESCE(m.is_rental, 0) = 1" in sql
    assert "LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa%%'" not in sql
    assert "LOWER(COALESCE(m.internal_report, '')) LIKE '%%sewa%%'" not in sql
    assert "LOWER(COALESCE(m.tax_report, '')) LIKE '%%sewa%%'" not in sql
    assert "LOWER(COALESCE(t.description, '')) LIKE '%%sewa%%'" not in sql
    assert "LOWER(COALESCE(t.description, '')) LIKE '%%rent%%'" not in sql
    assert "coa.code IN ('5315', '5105')" not in sql


def test_linkable_transactions_query_matches_same_rental_mark_rule():
    sql = str(build_linkable_transactions_query())

    assert "t.rental_contract_id = :current_contract_id" in sql
    assert "COALESCE(m.is_rental, 0) = 1" in sql
    assert "LOWER(COALESCE(m.personal_use, '')) LIKE '%%sewa%%'" not in sql
    assert "LOWER(COALESCE(m.internal_report, '')) LIKE '%%sewa%%'" not in sql
    assert "LOWER(COALESCE(m.tax_report, '')) LIKE '%%sewa%%'" not in sql
    assert "LOWER(COALESCE(t.description, '')) LIKE '%%sewa%%'" not in sql
    assert "LOWER(COALESCE(t.description, '')) LIKE '%%rent%%'" not in sql
    assert "coa.code IN ('5315', '5105')" not in sql
