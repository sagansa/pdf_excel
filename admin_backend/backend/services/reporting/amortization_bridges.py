import json
import logging

from sqlalchemy import text

from backend.services.reporting.rental_adjustments import _calculate_cumulative_rental_amortization_as_of
from backend.services.reporting.report_amortization_common import _calculate_accumulated_amortization
from backend.services.reporting.report_sql_fragments import (
    _coretax_filter_clause,
    _mark_coa_join_clause,
    _split_parent_exclusion_clause,
)
from backend.services.reporting.report_value_utils import (
    _parse_bool,
    _parse_date,
)
from backend.services.reporting.equity_bridges import add_or_update_asset_item, resolve_prepaid_asset_code

logger = logging.getLogger(__name__)


def apply_prepaid_rent_amortization_bridge(conn, asset_items, as_of_date, company_id, report_type):
    try:
        cumulative_amortization = _calculate_cumulative_rental_amortization_as_of(conn, as_of_date, company_id, report_type)
        if abs(cumulative_amortization) < 0.000001:
            return

        prepaid_coa_code = resolve_prepaid_asset_code(conn, company_id)
        if prepaid_coa_code in asset_items:
            asset_items[prepaid_coa_code]['amount'] -= cumulative_amortization
            if abs(asset_items[prepaid_coa_code]['amount']) < 0.000001:
                del asset_items[prepaid_coa_code]
    except Exception as exc:
        logger.error('Failed to bridge prepaid rent amortization in balance sheet: %s', exc)


def apply_manual_amortization_bridge(conn, asset_items, as_of_date_obj, as_of_date, company_id, report_type):
    try:
        allow_partial_year = True
        use_mark_based_amortization = False
        for row in conn.execute(text("""
            SELECT setting_name, setting_value
            FROM amortization_settings
            WHERE setting_name IN ('allow_partial_year', 'use_mark_based_amortization')
              AND (company_id = :company_id OR company_id IS NULL)
            ORDER BY company_id ASC
        """), {'company_id': company_id}):
            if row.setting_name == 'allow_partial_year':
                allow_partial_year = _parse_bool(row.setting_value)
            elif row.setting_name == 'use_mark_based_amortization':
                use_mark_based_amortization = _parse_bool(row.setting_value)

        accumulated_code_by_type = {
            'Building': '1524',
            'Tangible': '1530',
            'LandRights': '1534',
            'Intangible': '1601',
        }
        for row in conn.execute(text("""
            SELECT setting_value
            FROM amortization_settings
            WHERE setting_name = 'accumulated_depreciation_coa_codes'
              AND (company_id = :company_id OR company_id IS NULL)
            ORDER BY company_id ASC
        """), {'company_id': company_id}):
            try:
                parsed = json.loads(row.setting_value)
                if isinstance(parsed, dict):
                    accumulated_code_by_type.update(parsed)
            except Exception:
                continue

        asset_code_by_type = {
            'Building': '1523',
            'Tangible': '1529',
            'LandRights': '1533',
            'Intangible': '1600',
        }

        journaled_descriptions = set()
        if company_id:
            journaled_descriptions = {
                (row.item_description or '').strip()
                for row in conn.execute(text("""
                    SELECT DISTINCT TRIM(REPLACE(t.description, 'Manual Amortization - ', '')) AS item_description
                    FROM transactions t
                    WHERE t.source_file = 'manual_amortization_journal'
                      AND t.txn_date <= :as_of_date
                      AND t.company_id = :company_id
                """), {'as_of_date': as_of_date, 'company_id': company_id})
            }

        asset_totals = {}
        accum_totals = {}
        manual_result = conn.execute(text("""
            SELECT
                ai.id,
                ai.description,
                ai.amount,
                ai.amortization_date,
                ai.use_half_rate,
                ag.asset_type,
                ag.tarif_rate
            FROM amortization_items ai
            LEFT JOIN amortization_asset_groups ag ON ai.asset_group_id = ag.id
            WHERE ai.is_manual = TRUE
              AND ai.asset_group_id IS NOT NULL
              AND ai.amount > 0
              AND ai.amortization_date IS NOT NULL
              AND ai.amortization_date <= :as_of_date
              AND (:company_id IS NULL OR ai.company_id = :company_id)
            ORDER BY ai.amortization_date ASC
        """), {'as_of_date': as_of_date, 'company_id': company_id})

        for row in manual_result:
            description = (row.description or '').strip()
            if company_id and description and description in journaled_descriptions:
                continue

            amount = float(row.amount or 0)
            start_date = _parse_date(row.amortization_date)
            if amount <= 0 or start_date is None:
                continue

            asset_type = row.asset_type or 'Tangible'
            asset_code = asset_code_by_type.get(asset_type, asset_code_by_type['Tangible'])
            accum_code = accumulated_code_by_type.get(asset_type, accumulated_code_by_type['Tangible'])
            rate = float(row.tarif_rate or 20)

            accumulated_amount = _calculate_accumulated_amortization(
                amount,
                rate,
                start_date,
                as_of_date_obj,
                use_half_rate=_parse_bool(row.use_half_rate),
                allow_partial_year=allow_partial_year,
            )
            asset_totals[asset_code] = asset_totals.get(asset_code, 0.0) + amount
            accum_totals[accum_code] = accum_totals.get(accum_code, 0.0) - accumulated_amount

        if use_mark_based_amortization:
            mark_coa_join_txn = _mark_coa_join_clause(
                conn, report_type, mark_ref='t.mark_id', mapping_alias='mcm', join_type='INNER'
            )
            for row in conn.execute(text(f"""
                SELECT DISTINCT
                    t.id,
                    CASE WHEN t.db_cr = 'CR' THEN -t.amount ELSE t.amount END AS acquisition_cost,
                    t.amortization_start_date,
                    t.txn_date,
                    t.use_half_rate,
                    ag.asset_type,
                    ag.tarif_rate
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                {mark_coa_join_txn}
                INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id
                INNER JOIN amortization_asset_groups ag ON t.amortization_asset_group_id = ag.id
                WHERE coa.category = 'ASSET'
                  AND t.txn_date <= :as_of_date
                  AND (:company_id IS NULL OR t.company_id = :company_id)
                  {_split_parent_exclusion_clause(conn, 't')}
                  {_coretax_filter_clause(conn, report_type, 'm')}
            """), {'as_of_date': as_of_date, 'company_id': company_id}):
                amount = float(row.acquisition_cost or 0)
                if amount == 0:
                    continue
                start_date = _parse_date(row.amortization_start_date) or _parse_date(row.txn_date)
                if not start_date or start_date > as_of_date_obj:
                    continue
                asset_type = row.asset_type or 'Tangible'
                accum_code = accumulated_code_by_type.get(asset_type, accumulated_code_by_type['Tangible'])
                rate = float(row.tarif_rate or 20)
                accum_amount = _calculate_accumulated_amortization(
                    amount,
                    rate,
                    start_date,
                    as_of_date_obj,
                    use_half_rate=_parse_bool(row.use_half_rate),
                    allow_partial_year=allow_partial_year,
                )
                accum_totals[accum_code] = accum_totals.get(accum_code, 0.0) - accum_amount

        # REFACTORED: Include amortization assets for both 'real' and 'coretax'
        # Previously excluded for coretax, causing incomplete balance sheet data
        for row in conn.execute(text("""
            SELECT
                a.acquisition_cost,
                a.acquisition_date,
                a.amortization_start_date,
                a.use_half_rate,
                ag.asset_type,
                ag.tarif_rate
            FROM amortization_assets a
            LEFT JOIN amortization_asset_groups ag ON a.asset_group_id = ag.id
            WHERE (a.is_active = TRUE OR a.is_active = 1)
              AND a.acquisition_date <= :as_of_date
              AND (:company_id IS NULL OR a.company_id = :company_id)
        """), {'as_of_date': as_of_date, 'company_id': company_id}):
            amount = float(row.acquisition_cost or 0)
            if amount <= 0:
                continue
            start_date = _parse_date(row.amortization_start_date) or _parse_date(row.acquisition_date)
            if not start_date or start_date > as_of_date_obj:
                continue
            asset_type = row.asset_type or 'Tangible'
            accum_code = accumulated_code_by_type.get(asset_type, accumulated_code_by_type['Tangible'])
            rate = float(row.tarif_rate or 20)
            accum_amount = _calculate_accumulated_amortization(
                amount,
                rate,
                start_date,
                as_of_date_obj,
                use_half_rate=_parse_bool(row.use_half_rate),
                allow_partial_year=allow_partial_year,
            )
            accum_totals[accum_code] = accum_totals.get(accum_code, 0.0) - accum_amount

        all_codes = list(set(asset_totals.keys()) | set(accum_totals.keys()))
        coa_lookup = {}
        if all_codes:
            for row in conn.execute(text("""
                SELECT id, code, name, subcategory
                FROM chart_of_accounts
                WHERE code IN :codes
            """), {'codes': tuple(all_codes)}):
                coa_lookup[row.code] = row._mapping

        for code, amount in asset_totals.items():
            coa_info = coa_lookup.get(code, {})
            add_or_update_asset_item(
                asset_items,
                coa_info.get('id', f'manual_{code}_asset'),
                code,
                coa_info.get('name', f'Manual Asset ({code})'),
                coa_info.get('subcategory', 'Non-Current Assets'),
                amount,
                force_current=False,
            )

        for code, amount in accum_totals.items():
            if abs(amount) < 0.000001:
                continue
            coa_info = coa_lookup.get(code, {})
            add_or_update_asset_item(
                asset_items,
                coa_info.get('id', f'manual_{code}_accum'),
                code,
                coa_info.get('name', f'Akumulasi Amortisasi ({code})'),
                coa_info.get('subcategory', 'Non-Current Assets'),
                amount,
                force_current=False,
            )
    except Exception as exc:
        logger.error('Failed to process manual amortization bridge data: %s', exc)
