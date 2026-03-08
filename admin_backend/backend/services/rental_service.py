import uuid
import datetime

from backend.db.session import get_db_engine
from backend.services.rental_accounting_helpers import (
    get_supported_table_columns,
    resolve_cash_account,
    resolve_coa_by_setting,
)
from backend.services.rental_financials import (
    DEFAULT_TAX_RATE,
    build_amortization_schedule,
    calculate_rent_components,
    extract_cfg_from_notes,
    month_span,
    normalize_calculation_method,
    normalize_pph42_timing,
    parse_date,
    to_float,
)
from backend.services.rental_journal_builder import build_journal_preview
from backend.services.rental_prepaid_queries import (
    build_contract_lookup_query,
    build_contract_payment_stats_query,
    build_existing_prepaid_by_contract_query,
    build_existing_prepaid_by_id_query,
    build_insert_prepaid_query,
    build_update_contract_query,
    build_update_prepaid_query,
)

# Prepaid rent module is retired. Keep journal preview logic, but disable DB upsert.
PREPAID_RENT_FEATURE_ENABLED = False


def create_or_update_prepaid_from_contract(contract_id, company_id, accounting_options=None):
    """
    Create/update prepaid expense from rental contract and return journal preview.
    accounting_options:
      - calculation_method: BRUTO | NETTO
      - pph42_rate: number
      - pph42_payment_timing: same_period | next_period | next_year
      - pph42_payment_date: YYYY-MM-DD
      - preview_only: bool
    """
    if not contract_id:
        return {}

    accounting_options = accounting_options or {}
    preview_only = bool(accounting_options.get('preview_only', False)) or (not PREPAID_RENT_FEATURE_ENABLED)

    engine, error_msg = get_db_engine()
    if engine is None:
        return {'error': error_msg}

    with engine.begin() as conn:
        store_cols = get_supported_table_columns(conn, 'rental_stores')
        store_name_sql = "s.store_name" if 'store_name' in store_cols else "s.name"

        contract = conn.execute(build_contract_lookup_query(store_name_sql), {
            'id': contract_id,
            'company_id': company_id
        }).mappings().first()

        if not contract:
            return {'error': 'Rental contract not found'}

        stats = conn.execute(
            build_contract_payment_stats_query(),
            {'contract_id': contract_id}
        ).mappings().first()

        txn_count = int(stats['txn_count'] or 0)
        linked_total = to_float(stats['total_paid'], 0.0)

        base_amount = linked_total if linked_total > 0 else to_float(contract.get('total_amount'), 0.0)
        if base_amount <= 0:
            return {
                'created': False,
                'updated': False,
                'prepaid_id': contract.get('prepaid_expense_id'),
                'total_amount': 0.0,
                'amount_bruto': 0.0,
                'amount_net': 0.0,
                'amount_tax': 0.0,
                'transaction_count': txn_count,
                'error': 'No linked payment amount found'
            }

        table_columns = get_supported_table_columns(conn, 'rental_contracts')
        notes_cfg = extract_cfg_from_notes(contract.get('notes'))
        contract_method = accounting_options.get('calculation_method')
        if not contract_method:
            if 'calculation_method' in table_columns:
                contract_method = contract.get('calculation_method')
            if not contract_method:
                contract_method = notes_cfg.get('calculation_method')

        contract_rate = accounting_options.get('pph42_rate')
        if contract_rate is None:
            if 'pph42_rate' in table_columns:
                contract_rate = contract.get('pph42_rate')
            if contract_rate is None:
                contract_rate = notes_cfg.get('pph42_rate')

        contract_timing = accounting_options.get('pph42_payment_timing')
        if not contract_timing:
            if 'pph42_payment_timing' in table_columns:
                contract_timing = contract.get('pph42_payment_timing')
            if not contract_timing:
                contract_timing = notes_cfg.get('pph42_payment_timing')

        contract_payment_date = accounting_options.get('pph42_payment_date')
        if not contract_payment_date:
            if 'pph42_payment_date' in table_columns:
                contract_payment_date = contract.get('pph42_payment_date')
            if not contract_payment_date:
                contract_payment_date = notes_cfg.get('pph42_payment_date')

        calculation_method = normalize_calculation_method(contract_method)
        pph42_timing = normalize_pph42_timing(contract_timing)
        pph42_rate = to_float(contract_rate, DEFAULT_TAX_RATE)

        financials = calculate_rent_components(base_amount, calculation_method, pph42_rate)
        financials['total_paid'] = linked_total
        financials['first_payment_date'] = stats.get('first_payment_date')

        start_date = parse_date(contract.get('start_date'))
        end_date = parse_date(contract.get('end_date')) or start_date
        duration_months = month_span(start_date, end_date)
        monthly_amount = round(financials['amount_bruto'] / max(duration_months, 1), 2)

        prepaid_coa = resolve_coa_by_setting(conn, company_id, 'prepaid_prepaid_asset_coa', ['1421', '1135'])
        expense_coa = resolve_coa_by_setting(conn, company_id, 'prepaid_rent_expense_coa', ['5315', '5105'])
        tax_coa = resolve_coa_by_setting(conn, company_id, 'prepaid_tax_payable_coa', ['2191', '2141'])
        cash_coa = resolve_cash_account(conn, company_id)

        prepaid_table_columns = get_supported_table_columns(conn, 'prepaid_expenses')

        existing_prepaid = None
        if 'contract_id' in prepaid_table_columns:
            existing_prepaid = conn.execute(
                build_existing_prepaid_by_contract_query(),
                {'contract_id': contract_id}
            ).mappings().first()

        if not existing_prepaid and contract.get('prepaid_expense_id'):
            existing_prepaid = conn.execute(
                build_existing_prepaid_by_id_query(),
                {'id': contract['prepaid_expense_id']}
            ).mappings().first()

        prepaid_id = existing_prepaid['id'] if existing_prepaid else (None if not PREPAID_RENT_FEATURE_ENABLED else str(uuid.uuid4()))

        if preview_only:
            prepaid_was_created = False
            prepaid_was_updated = False
        else:
            payload = {
                'id': prepaid_id,
                'company_id': contract.get('company_id') or company_id,
                'description': f"Sewa {contract.get('store_name') or '-'} - {contract.get('location_name') or '-'}",
                'contract_id': contract_id,
                'prepaid_coa_id': prepaid_coa['id'],
                'expense_coa_id': expense_coa['id'],
                'tax_payable_coa_id': tax_coa['id'],
                'start_date': start_date,
                'end_date': end_date,
                'duration_months': duration_months,
                'amount_net': round(financials['amount_net'], 2),
                'amount_bruto': round(financials['amount_bruto'], 2),
                'amount_tax': round(financials['amount_tax'], 2),
                'monthly_amortization': monthly_amount,
                'tax_rate': round(financials['tax_rate'], 4),
                'is_gross_up': calculation_method == 'NETTO',
                'is_active': True,
                'notes': (
                    f"[AUTO RENTAL] method={calculation_method}; pph42_rate={financials['tax_rate']}; "
                    f"pph42_timing={pph42_timing}; linked_paid={linked_total}"
                ),
                'created_at': datetime.datetime.now(),
                'updated_at': datetime.datetime.now()
            }

            insert_columns = [k for k in payload.keys() if k in prepaid_table_columns]
            if not insert_columns:
                return {
                    'error': 'prepaid_expenses table has no compatible columns for auto-upsert',
                    'created': False,
                    'updated': False,
                    'prepaid_id': existing_prepaid['id'] if existing_prepaid else None
                }

            if existing_prepaid:
                update_columns = [k for k in insert_columns if k != 'id']
                if not update_columns:
                    return {
                        'error': 'prepaid_expenses update columns are not available',
                        'created': False,
                        'updated': False,
                        'prepaid_id': existing_prepaid['id']
                    }
                set_clause = ', '.join(f"{column} = :{column}" for column in update_columns)
                conn.execute(build_update_prepaid_query(set_clause), payload)
                prepaid_was_created = False
                prepaid_was_updated = True
            else:
                columns_sql = ', '.join(insert_columns)
                values_sql = ', '.join(f":{column}" for column in insert_columns)
                conn.execute(build_insert_prepaid_query(columns_sql, values_sql), payload)
                prepaid_was_created = True
                prepaid_was_updated = False

            contract_updates = {'id': contract_id}
            update_fields = []
            if 'prepaid_expense_id' in table_columns:
                contract_updates['prepaid_expense_id'] = prepaid_id
                update_fields.append('prepaid_expense_id = :prepaid_expense_id')
            if 'total_amount' in table_columns:
                contract_updates['total_amount'] = round(financials['amount_bruto'], 2)
                update_fields.append('total_amount = :total_amount')
            if 'calculation_method' in table_columns:
                contract_updates['calculation_method'] = calculation_method
                update_fields.append('calculation_method = :calculation_method')
            if 'pph42_rate' in table_columns:
                contract_updates['pph42_rate'] = round(financials['tax_rate'], 4)
                update_fields.append('pph42_rate = :pph42_rate')
            if 'pph42_payment_timing' in table_columns:
                contract_updates['pph42_payment_timing'] = pph42_timing
                update_fields.append('pph42_payment_timing = :pph42_payment_timing')
            if 'pph42_payment_date' in table_columns:
                contract_updates['pph42_payment_date'] = parse_date(contract_payment_date)
                update_fields.append('pph42_payment_date = :pph42_payment_date')

            if update_fields:
                update_sql = ', '.join(update_fields)
                conn.execute(build_update_contract_query(update_sql), contract_updates)

        coa_map = {
            'prepaid': prepaid_coa,
            'expense': expense_coa,
            'tax_payable': tax_coa,
            'cash': cash_coa
        }

        amortization_schedule = build_amortization_schedule(start_date, duration_months, monthly_amount)
        journals = build_journal_preview(
            contract=contract,
            coa_map=coa_map,
            financials=financials,
            pph42_timing=pph42_timing,
            pph42_payment_date=contract_payment_date,
            amortization_schedule=amortization_schedule
        )

        result = {
            'created': prepaid_was_created,
            'updated': prepaid_was_updated,
            'prepaid_id': prepaid_id,
            'transaction_count': txn_count,
            'total_amount': round(base_amount, 2),
            'amount_bruto': round(financials['amount_bruto'], 2),
            'amount_net': round(financials['amount_net'], 2),
            'amount_tax': round(financials['amount_tax'], 2),
            'tax_rate': round(financials['tax_rate'], 4),
            'calculation_method': calculation_method,
            'pph42_payment_timing': pph42_timing,
            'monthly_amortization': monthly_amount,
            'duration_months': duration_months,
            'journals': journals,
            'amortization_schedule': amortization_schedule
        }
        if not PREPAID_RENT_FEATURE_ENABLED:
            result['disabled'] = True
        return result


def generate_contract_journal_preview(contract_id, company_id, accounting_options=None):
    preview_options = dict(accounting_options or {})
    preview_options['preview_only'] = True
    return create_or_update_prepaid_from_contract(contract_id, company_id, preview_options)
