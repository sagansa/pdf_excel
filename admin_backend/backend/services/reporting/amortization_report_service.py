from backend.routes.amortization.amortization_helpers import (
    build_manual_item_payload,
    build_registered_asset_payload,
    load_amortization_defaults,
)
from backend.routes.amortization.amortization_queries import (
    amortization_assets_query,
    amortization_items_query,
    amortization_settings_query,
)


def fetch_amortization_report_data(conn, year, company_id):
    settings_rows = conn.execute(amortization_settings_query(), {'company_id': company_id}).fetchall()
    defaults = load_amortization_defaults(settings_rows)
    default_rate = defaults['default_rate']
    default_life = defaults['default_life']
    allow_partial_year = defaults['allow_partial_year']

    items_result = conn.execute(amortization_items_query(), {'company_id': company_id, 'year': year})
    items = []
    manual_total_amort = 0.0
    automatic_total_amort = 0.0
    total_amount = 0.0

    for row in items_result:
        item_payload, annual_amortization = build_manual_item_payload(row._mapping, int(year), allow_partial_year)
        if not item_payload:
            continue
        items.append(item_payload)
        total_amount += float(item_payload.get('amount', 0) or 0)
        manual_total_amort += annual_amortization

    assets_result = conn.execute(amortization_assets_query(), {'company_id': company_id})

    for row in assets_result:
        asset_payload, current_year_amort, base_amount = build_registered_asset_payload(
            row._mapping, int(year), default_rate, default_life, allow_partial_year
        )
        if not asset_payload:
            continue
        items.append(asset_payload)
        total_amount += base_amount
        automatic_total_amort += current_year_amort

    return {
        'items': items,
        'totalAmount': total_amount,
        'manual_total': manual_total_amort,
        'calculated_total': automatic_total_amort,
        'grand_total': manual_total_amort + automatic_total_amort,
        'settings': {},
    }
