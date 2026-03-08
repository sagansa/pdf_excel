from sqlalchemy import bindparam, text


def first_company_query():
    return text("SELECT id FROM companies LIMIT 1")


def amortization_settings_query():
    return text("""
        SELECT setting_name, setting_value, setting_type
        FROM amortization_settings
        WHERE company_id = :company_id OR company_id IS NULL
        ORDER BY company_id ASC
    """)


def amortization_items_query():
    return text("""
        SELECT
            ai.id, ai.company_id, ai.year,
            COALESCE(ai.mark_id, ai.coa_id) as mark_id,
            COALESCE(m.personal_use, coa.name) as mark_name,
            ai.coa_id, coa.code as coa_code, coa.name as coa_name,
            ai.description, ai.amount, ai.amortization_date,
            ai.asset_group_id, ai.use_half_rate, ai.notes, ai.is_manual,
            ai.created_at, ai.updated_at,
            ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type
        FROM amortization_items ai
        LEFT JOIN chart_of_accounts coa ON ai.coa_id = coa.id
        LEFT JOIN marks m ON ai.mark_id = m.id
        LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
        WHERE ai.company_id = :company_id
        ORDER BY ai.amortization_date ASC, ai.created_at ASC
    """)


def amortization_assets_query():
    return text("""
        SELECT
            a.id as asset_id, a.asset_name, a.asset_description as description,
            a.acquisition_cost, a.acquisition_date,
            a.amortization_start_date, a.asset_group_id, a.use_half_rate,
            ag.group_name, ag.tarif_rate, ag.useful_life_years, ag.asset_type
        FROM amortization_assets a
        LEFT JOIN amortization_asset_groups ag ON a.asset_group_id = ag.id
        WHERE (a.company_id = :company_id OR :company_id IS NULL)
        AND a.is_active = TRUE
        ORDER BY a.acquisition_date ASC, a.created_at ASC
    """)


def manual_amortization_items_query():
    return text("""
        SELECT ai.*, m.personal_use as mark_name,
               ag.group_name, ag.tarif_rate, ag.asset_type
        FROM amortization_items ai
        LEFT JOIN marks m ON ai.mark_id = m.id
        LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
        WHERE ai.company_id = :company_id
        AND ai.year = :year
        AND ai.is_manual = TRUE
    """)


def existing_manual_journal_query():
    return text("""
        SELECT COUNT(*) as count
        FROM transactions t
        INNER JOIN marks m ON t.mark_id = m.id
        WHERE m.personal_use LIKE 'Manual Amortization-%'
        AND t.company_id = :company_id
        AND YEAR(t.txn_date) = :year
    """)


def coa_id_by_code_query():
    return text("SELECT id FROM chart_of_accounts WHERE code = :code")


def insert_mark_query():
    return text("""
        INSERT INTO marks (id, personal_use, internal_report, tax_report, created_at, updated_at)
        VALUES (:id, :name, 1, 1, NOW(), NOW())
    """)


def insert_mark_coa_mapping_query():
    return text("""
        INSERT INTO mark_coa_mapping (id, mark_id, coa_id, mapping_type, created_at, updated_at)
        VALUES (:id, :mark_id, :coa_id, :mapping_type, NOW(), NOW())
    """)


def insert_transaction_query():
    return text("""
        INSERT INTO transactions (id, txn_date, description, amount, db_cr, mark_id,
                         company_id, created_at, updated_at, source_file)
        VALUES (:id, :date, :desc, :amount, :db_cr, :mark_id,
                :company_id, NOW(), NOW(), :source)
    """)


def insert_amortization_item_query():
    return text("""
        INSERT INTO amortization_items (
            id, company_id, year, mark_id, description, amount,
            amortization_date, asset_group_id, use_half_rate, notes,
            is_manual, created_at, updated_at
        ) VALUES (
            :id, :company_id, :year, :mark_id, :description, :amount,
            :amortization_date, :asset_group_id, :use_half_rate, :notes,
            :is_manual, NOW(), NOW()
        )
    """)


def update_amortization_item_query():
    return text("""
        UPDATE amortization_items
        SET mark_id = :mark_id,
            description = :description,
            amount = :amount,
            amortization_date = :amortization_date,
            asset_group_id = :asset_group_id,
            use_half_rate = :use_half_rate,
            notes = :notes,
            updated_at = NOW()
        WHERE id = :id
    """)


def delete_amortization_item_query():
    return text("DELETE FROM amortization_items WHERE id = :id")


def pending_amortization_transactions_query(include_year=False, include_current_asset=False):
    year_filter = "AND YEAR(t.txn_date) <= :year" if include_year else ""
    asset_filter = "AND t.amortization_asset_id IS NULL"
    if include_current_asset:
        asset_filter = "AND (t.amortization_asset_id IS NULL OR t.amortization_asset_id = :current_asset_id)"
    return text(f"""
        SELECT DISTINCT
            t.id,
            t.txn_date,
            t.description,
            CASE
                WHEN t.db_cr = 'CR' THEN -t.amount
                ELSE t.amount
            END as amount,
            t.bank_code,
            m.personal_use as mark_name,
            m.internal_report,
            t.amortization_asset_id
        FROM transactions t
        JOIN marks m ON t.mark_id = m.id
        WHERE (t.company_id = :company_id OR :company_id IS NULL)
        AND m.is_asset = TRUE
        {asset_filter}
        {year_filter}
        ORDER BY t.txn_date ASC
    """)


def transaction_total_for_ids_query():
    return text("""
        SELECT SUM(CASE WHEN db_cr = 'CR' THEN -amount ELSE amount END) as total_cost
        FROM transactions
        WHERE company_id = :company_id AND id IN :transaction_ids
    """).bindparams(bindparam('transaction_ids', expanding=True))


def insert_amortization_asset_query():
    return text("""
        INSERT INTO amortization_assets (
            id, company_id, asset_group_id, asset_name,
            acquisition_date, acquisition_cost, amortization_start_date,
            is_active
        ) VALUES (
            :id, :company_id, :asset_group_id, :asset_name,
            :acquisition_date, :acquisition_cost, :acquisition_date,
            1
        )
    """)


def update_transactions_asset_link_query():
    return text("""
        UPDATE transactions
        SET amortization_asset_id = :asset_id
        WHERE company_id = :company_id AND id IN :transaction_ids
    """).bindparams(bindparam('transaction_ids', expanding=True))


def unlink_transactions_by_asset_query():
    return text("""
        UPDATE transactions
        SET amortization_asset_id = NULL
        WHERE amortization_asset_id = :asset_id
    """)


def update_amortization_asset_query(set_clause):
    return text(f"""
        UPDATE amortization_assets
        SET {set_clause}
        WHERE id = :asset_id
    """)


def delete_amortization_asset_query():
    return text("DELETE FROM amortization_assets WHERE id = :asset_id")
