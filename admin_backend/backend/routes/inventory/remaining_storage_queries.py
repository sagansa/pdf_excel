from sqlalchemy import text


def build_monitoring_query(
    smd_table,
    smd_monitoring_fk,
    coefficient_expr,
    product_unit_select,
    category_filter,
    remaining_for_filter,
    date_filter_sql,
    stock_date_column,
):
    return text(f"""
        SELECT
            sm.id AS monitoring_id,
            sm.name AS monitoring_name,
            sm.quantity_low,
            sm.category,
            smd.id AS monitoring_detail_id,
            smd.`product_id` AS product_id,
            {coefficient_expr} AS coefficient_value,
            p.name AS product_name,
            {product_unit_select},
            latest.remaining_quantity,
            latest.stock_card_date
        FROM stock_monitorings sm
        LEFT JOIN {smd_table} smd
            ON smd.`{smd_monitoring_fk}` = sm.id
        LEFT JOIN products p
            ON p.id = smd.`product_id`
        LEFT JOIN units pu
            ON pu.id = p.unit_id
        LEFT JOIN (
            SELECT
                latest_dates.product_id,
                latest_dates.latest_date AS stock_card_date,
                SUM(dsc.quantity) AS remaining_quantity
            FROM (
                SELECT
                    dsc.product_id,
                    MAX(sc.`{stock_date_column}`) AS latest_date
                FROM detail_stock_cards dsc
                INNER JOIN stock_cards sc
                    ON sc.id = dsc.stock_card_id
                WHERE {remaining_for_filter}
                {date_filter_sql}
                GROUP BY dsc.product_id
            ) latest_dates
            INNER JOIN detail_stock_cards dsc
                ON dsc.product_id = latest_dates.product_id
            INNER JOIN stock_cards sc
                ON sc.id = dsc.stock_card_id
               AND sc.`{stock_date_column}` = latest_dates.latest_date
            WHERE {remaining_for_filter}
            {date_filter_sql}
            GROUP BY latest_dates.product_id, latest_dates.latest_date
        ) latest
            ON latest.product_id = smd.`product_id`
        {category_filter}
        ORDER BY sm.name ASC, p.name ASC
    """)


def build_monitoring_definition_query(
    smd_table,
    smd_monitoring_fk,
    coefficient_expr,
    product_unit_select,
    category_filter,
):
    return text(f"""
        SELECT
            sm.id AS monitoring_id,
            sm.name AS monitoring_name,
            sm.quantity_low,
            sm.category,
            smd.id AS monitoring_detail_id,
            smd.`product_id` AS product_id,
            {coefficient_expr} AS coefficient_value,
            p.name AS product_name,
            {product_unit_select}
        FROM stock_monitorings sm
        LEFT JOIN {smd_table} smd
            ON smd.`{smd_monitoring_fk}` = sm.id
        LEFT JOIN products p
            ON p.id = smd.`product_id`
        LEFT JOIN units pu
            ON pu.id = p.unit_id
        {category_filter}
        ORDER BY sm.name ASC, p.name ASC
    """)


def build_all_store_query(
    store_name_column=None,
    stores_columns=None,
    has_store_column=False,
    status_column=None,
    excluded_status=None,
):
    status_filter = ''
    if status_column and excluded_status is not None:
        status_filter = f"WHERE (s.`{status_column}` IS NULL OR s.`{status_column}` <> {int(excluded_status)})"

    if store_name_column:
        return text(f"""
            SELECT
                CAST(s.id AS CHAR) AS store_id,
                NULLIF(TRIM(s.`{store_name_column}`), '') AS store_name
            FROM stores s
            {status_filter}
            ORDER BY s.`{store_name_column}` ASC
        """)
    if stores_columns:
        return text("""
            SELECT
                CAST(s.id AS CHAR) AS store_id,
                CAST(s.id AS CHAR) AS store_name
            FROM stores s
            {status_filter}
            ORDER BY s.id ASC
        """.replace('{status_filter}', status_filter))
    if has_store_column:
        return text("""
            SELECT DISTINCT
                CAST(sc.store_id AS CHAR) AS store_id,
                CAST(sc.store_id AS CHAR) AS store_name
            FROM stock_cards sc
            WHERE sc.store_id IS NOT NULL
            ORDER BY sc.store_id ASC
        """)
    return None


def build_reported_store_query(remaining_for_filter, stock_date_column):
    return text(f"""
        SELECT DISTINCT
            CAST(sc.store_id AS CHAR) AS store_id
        FROM stock_cards sc
        WHERE {remaining_for_filter}
          AND sc.store_id IS NOT NULL
          AND DATE(sc.`{stock_date_column}`) = :selected_date
    """)
