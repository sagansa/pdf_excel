from sqlalchemy import text

from backend.services.report_value_utils import _to_float


def _get_inventory_balance_with_carry(conn, year, company_id=None, report_type='real'):
    year = int(year)
    current_query = text("""
        SELECT beginning_inventory_amount, beginning_inventory_qty,
               ending_inventory_amount, ending_inventory_qty
        FROM inventory_balances
        WHERE year = :year AND (:company_id IS NULL OR company_id = :company_id)
        ORDER BY updated_at DESC, created_at DESC
        LIMIT 1
    """)
    current = conn.execute(current_query, {'year': year, 'company_id': company_id}).fetchone()

    beginning_amount = _to_float(current[0], 0.0) if current else 0.0
    beginning_qty = _to_float(current[1], 0.0) if current else 0.0
    ending_amount = _to_float(current[2], 0.0) if current else 0.0
    ending_qty = _to_float(current[3], 0.0) if current else 0.0

    if abs(beginning_amount) < 0.000001 and abs(beginning_qty) < 0.000001:
        prev_query = text("""
            SELECT ending_inventory_amount, ending_inventory_qty
            FROM inventory_balances
            WHERE year = :year AND (:company_id IS NULL OR company_id = :company_id)
            ORDER BY updated_at DESC, created_at DESC
            LIMIT 1
        """)
        previous = conn.execute(prev_query, {'year': year - 1, 'company_id': company_id}).fetchone()
        if previous:
            prev_ending_amount = _to_float(previous[0], 0.0)
            prev_ending_qty = _to_float(previous[1], 0.0)
            if abs(prev_ending_amount) >= 0.000001 or abs(prev_ending_qty) >= 0.000001:
                beginning_amount = prev_ending_amount
                beginning_qty = prev_ending_qty

    return {
        'beginning_inventory_amount': beginning_amount,
        'beginning_inventory_qty': beginning_qty,
        'ending_inventory_amount': ending_amount,
        'ending_inventory_qty': ending_qty,
    }
