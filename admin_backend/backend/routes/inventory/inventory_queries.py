from sqlalchemy import text


def inventory_balance_id_query():
    return text("""
        SELECT id FROM inventory_balances
        WHERE year = :year AND company_id = :company_id
    """)


def update_inventory_balance_query():
    return text("""
        UPDATE inventory_balances SET
            beginning_inventory_amount = :beginning_amount,
            beginning_inventory_qty = :beginning_qty,
            ending_inventory_amount = :ending_amount,
            ending_inventory_qty = :ending_qty,
            base_value = :base_value,
            is_manual = 1,
            updated_at = :updated_at
        WHERE year = :year AND company_id = :company_id
    """)


def insert_inventory_balance_query():
    return text("""
        INSERT INTO inventory_balances (
            id, company_id, year,
            beginning_inventory_amount, beginning_inventory_qty,
            ending_inventory_amount, ending_inventory_qty,
            base_value, is_manual, created_at, updated_at
        ) VALUES (
            :id, :company_id, :year,
            :beginning_amount, :beginning_qty,
            :ending_amount, :ending_qty,
            :base_value, 1, :created_at, :updated_at
        )
    """)


def insert_carry_forward_inventory_balance_query():
    return text("""
        INSERT INTO inventory_balances (
            id, company_id, year,
            beginning_inventory_amount, beginning_inventory_qty,
            ending_inventory_amount, ending_inventory_qty,
            base_value, is_carry_forward, is_manual, created_at, updated_at
        ) VALUES (
            :id, :company_id, :year,
            :beginning_amount, :beginning_qty,
            0, 0,
            :base_value, 1, 0, :created_at, :updated_at
        )
    """)
