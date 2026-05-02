from backend.services.reporting.balance_sheet_service import (
    _apply_coretax_cash_receivable_reclassification,
    _split_asset_sections,
    _sum_reportable_items,
)


def test_coretax_reclassifies_negative_cash_with_related_receivable_as_display_history():
    asset_items = {
        '1101': {
            'id': 'cash-id',
            'code': '1101',
            'name': 'Kas dan Setara Kas',
            'subcategory': 'Current Assets',
            'amount': -20.0,
            'category': 'ASSET',
            'is_current': True,
        },
        '1125': {
            'id': 'receivable-id',
            'code': '1125',
            'name': 'Piutang Lainnya - Hubungan Istimewa',
            'subcategory': 'Current Assets',
            'amount': 50.0,
            'category': 'ASSET',
            'is_current': True,
        },
    }

    adjustment = _apply_coretax_cash_receivable_reclassification(
        asset_items,
        '2026-04-29',
        'company-1',
        'coretax',
    )
    current_assets, non_current_assets = _split_asset_sections(asset_items)

    assert adjustment == {
        'cash_code': '1101',
        'related_receivable_code': '1125',
        'original_cash_amount': -20.0,
        'original_related_receivable_amount': 50.0,
        'final_cash_amount': 30.0,
    }
    assert asset_items['1101']['amount'] == 30.0
    assert '1125' not in asset_items
    assert [item['name'] for item in current_assets] == [
        'Kas dan Setara Kas',
        'Kas dan Setara Kas (Historis Coretax)',
        'Piutang Lainnya - Hubungan Istimewa (Historis Coretax)',
    ]
    assert _sum_reportable_items(current_assets + non_current_assets) == 30.0
    assert all(
        item['hide_in_pdf'] is True
        for item in current_assets
        if item.get('is_display_only')
    )
    assert all(
        item['is_child_row'] is True and item['parent_code'] == '1101'
        for item in current_assets
        if item.get('is_display_only')
    )


def test_negative_cash_reclassification_is_coretax_only():
    asset_items = {
        '1101': {'code': '1101', 'amount': -20.0, 'is_current': True},
        '1125': {'code': '1125', 'amount': 50.0, 'is_current': True},
    }

    adjustment = _apply_coretax_cash_receivable_reclassification(
        asset_items,
        '2026-04-29',
        'company-1',
        'real',
    )

    assert adjustment is None
    assert asset_items['1101']['amount'] == -20.0
    assert asset_items['1125']['amount'] == 50.0
