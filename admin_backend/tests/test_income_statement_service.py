from backend.services.reporting.income_statement_service import (
    _build_earnings_metrics,
    _build_cogs_detail_items,
    _classify_positive_corrections,
    _merge_comparative_cogs,
)


def test_build_cogs_detail_items_does_not_mutate_purchase_totals():
    cogs_breakdown = {
        'beginning_inventory': 100.0,
        'ending_inventory': 40.0,
        'purchases': 250.0,
        'purchases_items': [{'code': '5001', 'amount': 250.0}],
        'other_cogs_items': [{'code': '5002', 'amount': 25.0}],
        'total_cogs': 335.0,
    }

    detail_items = _build_cogs_detail_items(cogs_breakdown)

    assert len(detail_items) == 1
    assert cogs_breakdown['purchases'] == 250.0
    assert cogs_breakdown['purchases_items'] == [{'code': '5001', 'amount': 250.0}]
    assert cogs_breakdown['other_cogs_items'] == [{'code': '5002', 'amount': 25.0}]


def test_merge_comparative_cogs_uses_previous_year_purchases_not_total_cogs():
    current_data = {
        'cogs_breakdown': {
            'purchases_items': [{'code': '5001', 'amount': 300.0}],
            'other_cogs_items': [{'code': '5002', 'amount': 50.0}],
        }
    }
    previous_year_data = {
        'cogs_breakdown': {
            'purchases': 125.0,
            'total_cogs': 999.0,
            'total_other_cogs': 20.0,
            'purchases_items': [{'code': '5001', 'amount': 125.0}],
            'other_cogs_items': [{'code': '5002', 'amount': 20.0}],
        }
    }

    _merge_comparative_cogs(current_data, previous_year_data)

    assert current_data['cogs_breakdown']['previous_year_purchases'] == 125.0
    assert current_data['cogs_breakdown']['previous_year_total_other_cogs'] == 20.0
    assert current_data['cogs_breakdown']['purchases_items'][0]['previous_year_amount'] == 125.0
    assert current_data['cogs_breakdown']['other_cogs_items'][0]['previous_year_amount'] == 20.0


def test_classify_positive_corrections_separates_tax_expense_accounts():
    items = [
        {
            'raw_components': [
                {
                    'code': '6101',
                    'name': 'Entertainment',
                    'amount': 10.0,
                    'fiscal_category': 'NON_DEDUCTIBLE_PERMANENT',
                },
                {
                    'code': '5494',
                    'name': 'Beban Pajak',
                    'amount': 20.0,
                    'fiscal_category': 'NON_DEDUCTIBLE_PERMANENT',
                },
            ]
        }
    ]

    positive_corrections, tax_expense_corrections = _classify_positive_corrections(items)

    assert [item['code'] for item in positive_corrections] == ['6101']
    assert [item['code'] for item in tax_expense_corrections] == ['5494']


def test_build_earnings_metrics_returns_ebt_eat_and_ebtda():
    metrics = _build_earnings_metrics(
        total_revenue=1000.0,
        total_expenses=300.0,
        total_cogs=200.0,
        depreciation_and_amortization=40.0,
        expenses=[
            {'code': '6101', 'amount': 100.0},
            {'code': '5491', 'amount': 25.0},
            {'code': '5494', 'amount': 15.0},
        ],
    )

    assert metrics['tax_expense'] == 40.0
    assert metrics['earnings_after_tax'] == 500.0
    assert metrics['earnings_before_tax'] == 540.0
    assert metrics['earnings_before_tax_depreciation_and_amortization'] == 580.0
