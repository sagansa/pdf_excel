from datetime import date
from types import SimpleNamespace

from backend.services.reporting import equity_bridges


class _FakeResult:
    def fetchone(self):
        return SimpleNamespace(
            min_start_year=2024,
            configured_previous_retained_earnings=1000.0,
        )


class _FakeConn:
    def execute(self, *_args, **_kwargs):
        return _FakeResult()


def test_append_retained_earnings_group_uses_parent_with_child_details(monkeypatch):
    net_income_by_period = {
        ('2024-01-01', '2024-12-31'): 100.0,
        ('2025-01-01', '2025-12-31'): 200.0,
        ('2026-01-01', '2026-04-29'): 300.0,
    }

    def fake_fetch_income_statement_data(_conn, start_date, end_date, *_args, **_kwargs):
        return {'net_income': net_income_by_period[(start_date, end_date)]}

    monkeypatch.setattr(
        equity_bridges,
        'fetch_income_statement_data',
        fake_fetch_income_statement_data,
    )

    equity = []

    retained_earnings = equity_bridges.append_retained_earnings_group(
        _FakeConn(),
        equity,
        date(2026, 4, 29),
        '2026-04-29',
        'company-1',
        'real',
    )

    assert retained_earnings == {
        'current_year_net_income': 300.0,
        'previous_year_retained_earnings': 1300.0,
        'retained_earnings_total': 1600.0,
    }
    assert [item['name'] for item in equity] == [
        'Laba Ditahan',
        'Laba/Rugi Tahun Berjalan',
        'Laba Ditahan Tahun Sebelumnya',
    ]
    assert equity[0]['amount'] == 1600.0
    assert equity[0]['is_parent_row'] is True
    assert equity[1]['is_child_row'] is True
    assert equity[1]['parent_code'] == '3200'
    assert equity[1]['exclude_from_total'] is True
    assert equity[1]['hide_in_pdf'] is True
    assert equity[2]['is_child_row'] is True
    assert equity[2]['parent_code'] == '3200'
    assert equity[2]['exclude_from_total'] is True
    assert equity[2]['hide_in_pdf'] is True
    assert sum(
        item['amount']
        for item in equity
        if not item.get('exclude_from_total')
    ) == 1600.0
