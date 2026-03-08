from sqlalchemy import text


def amortization_asset_groups_query(where_clause, include_company_order):
    order_clause = """
        ORDER BY asset_type, group_number,
                 CASE WHEN company_id = :company_id THEN 0 ELSE 1 END
    """ if include_company_order else """
        ORDER BY asset_type, group_number
    """
    return text(f"""
        SELECT id, group_name, group_number, asset_type, tarif_rate,
               tarif_half_rate, useful_life_years, company_id
        FROM amortization_asset_groups
        {where_clause}
        {order_clause}
    """)


def insert_amortization_asset_group_query():
    return text("""
        INSERT INTO amortization_asset_groups
        (id, company_id, group_name, group_number, asset_type,
         tarif_rate, tarif_half_rate, useful_life_years)
        VALUES
        (:id, :company_id, :group_name, :group_number, :asset_type,
         :tarif_rate, :tarif_half_rate, :useful_life_years)
    """)


def update_amortization_asset_group_query():
    return text("""
        UPDATE amortization_asset_groups
        SET group_name = :group_name,
            group_number = :group_number,
            asset_type = :asset_type,
            tarif_rate = :tarif_rate,
            tarif_half_rate = :tarif_half_rate,
            useful_life_years = :useful_life_years
        WHERE id = :id
    """)


def amortization_coa_codes_query():
    return text("""
        SELECT id, code, name, category, subcategory
        FROM chart_of_accounts
        WHERE code LIKE '531%' OR code LIKE '6%'
        ORDER BY code
    """)


def amortization_settings_query():
    return text("""
        SELECT setting_name, setting_value, setting_type
        FROM amortization_settings
        WHERE company_id = :company_id OR company_id IS NULL
        ORDER BY company_id ASC
    """)


def update_amortization_settings_query():
    return text("""
        UPDATE amortization_settings
        SET setting_value = :val,
            setting_type = :typ,
            updated_at = CURRENT_TIMESTAMP
        WHERE setting_name = :name
          AND (
            (:company_id IS NULL AND company_id IS NULL)
            OR company_id = :company_id
          )
    """)


def insert_amortization_settings_query():
    return text("""
        INSERT INTO amortization_settings
        (id, company_id, setting_name, setting_value, setting_type, created_at, updated_at)
        VALUES (:id, :company_id, :name, :val, :typ, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)


def mark_amortization_mappings_query():
    return text("""
        SELECT mam.*, m.personal_use as mark_name, ag.group_name,
               ag.tarif_rate as group_tarif_rate, ag.group_number
        FROM mark_amortization_mappings mam
        LEFT JOIN marks m ON mam.mark_id = m.id
        LEFT JOIN amortization_asset_groups ag ON mam.asset_group_id = ag.id
        ORDER BY m.personal_use, mam.asset_type
    """)


def insert_mark_amortization_mapping_query():
    return text("""
        INSERT INTO mark_amortization_mappings
        (id, mark_id, asset_type, useful_life_years, amortization_rate,
         asset_group_id, is_deductible_50_percent)
        VALUES
        (:id, :mark_id, :asset_type, :useful_life_years, :amortization_rate,
         :asset_group_id, :is_deductible_50_percent)
    """)


def update_mark_amortization_mapping_query():
    return text("""
        UPDATE mark_amortization_mappings
        SET mark_id = :mark_id, asset_type = :asset_type,
            useful_life_years = :useful_life_years, amortization_rate = :amortization_rate,
            asset_group_id = :asset_group_id, is_deductible_50_percent = :is_deductible_50_percent,
            updated_at = NOW()
        WHERE id = :id
    """)


def delete_mark_amortization_mapping_query():
    return text("DELETE FROM mark_amortization_mappings WHERE id = :id")


def mark_amortization_config_query():
    return text("""
        SELECT mam.*, m.personal_use as mark_name, ag.group_name,
               ag.tarif_rate as group_tarif_rate, ag.group_number
        FROM mark_amortization_mappings mam
        LEFT JOIN marks m ON mam.mark_id = m.id
        LEFT JOIN amortization_asset_groups ag ON mam.asset_group_id = ag.id
        WHERE mam.mark_id = :mark_id
    """)


def amortization_eligible_marks_query():
    return text("""
        SELECT DISTINCT m.id, m.personal_use,
               COALESCE(am.asset_type, 'Tangible') as asset_type
        FROM marks m
        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id
        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
        LEFT JOIN mark_amortization_mappings am ON m.id = am.mark_id
        WHERE (coa.code LIKE '1%' OR coa.code LIKE '15%' OR coa.code LIKE '16%')
          AND m.is_asset = 1
        ORDER BY m.personal_use
    """)
