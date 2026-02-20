import uuid
import datetime
import json
from decimal import Decimal
from sqlalchemy import text
from backend.db.session import get_db_engine

DEFAULT_TAX_RATE = 10.0
VALID_CALCULATION_METHODS = {'BRUTO', 'NETTO'}
VALID_PPH42_TIMINGS = {'same_period', 'next_period', 'next_year'}
RENT_CFG_PREFIX = '[RENT_CFG]'
# Prepaid rent module is retired. Keep journal preview logic, but disable DB upsert.
PREPAID_RENT_FEATURE_ENABLED = False


def _to_float(value, default=0.0):
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_calculation_method(value):
    method = str(value or 'BRUTO').strip().upper()
    if method not in VALID_CALCULATION_METHODS:
        return 'BRUTO'
    return method


def _normalize_pph42_timing(value):
    raw = str(value or 'same_period').strip().lower()
    alias_map = {
        'same_month': 'same_period',
        'same_year': 'same_period',
        'next_month': 'next_period',
    }
    normalized = alias_map.get(raw, raw)
    if normalized not in VALID_PPH42_TIMINGS:
        return 'same_period'
    return normalized


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _extract_cfg_from_notes(notes_value):
    text_value = str(notes_value or '')
    if RENT_CFG_PREFIX not in text_value:
        return {}
    _, _, tail = text_value.partition(RENT_CFG_PREFIX)
    try:
        cfg = json.loads(tail.strip())
        if isinstance(cfg, dict):
            return cfg
    except Exception:
        pass
    return {}


def _month_span(start_date, end_date):
    if not start_date or not end_date or end_date < start_date:
        return 1
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    return max(1, months)


def _get_table_columns(conn, table_name):
    allowed_tables = {
        'rental_contracts',
        'rental_stores',
        'rental_locations',
        'prepaid_expenses',
        'chart_of_accounts',
        'amortization_settings'
    }
    if table_name not in allowed_tables:
        return set()

    if conn.dialect.name == 'sqlite':
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return {str(row[1]) for row in rows}

    rows = conn.execute(text("""
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = :table_name
    """), {'table_name': table_name}).fetchall()
    return {str(row[0]) for row in rows}


def _get_setting_value(conn, company_id, setting_name):
    row = conn.execute(text("""
        SELECT setting_value
        FROM amortization_settings
        WHERE setting_name = :setting_name
          AND (company_id = :company_id OR company_id IS NULL)
        ORDER BY company_id DESC
        LIMIT 1
    """), {
        'setting_name': setting_name,
        'company_id': company_id
    }).fetchone()
    return row[0] if row else None


def _resolve_coa_by_setting(conn, company_id, setting_name, fallback_codes):
    if isinstance(fallback_codes, str):
        fallback_codes = [fallback_codes]
    fallback_codes = [str(code) for code in (fallback_codes or []) if str(code).strip()]

    value = _get_setting_value(conn, company_id, setting_name)
    coa_row = None

    if value:
        coa_row = conn.execute(text("""
            SELECT id, code, name
            FROM chart_of_accounts
            WHERE id = :value OR code = :value
            LIMIT 1
        """), {'value': str(value)}).fetchone()

    if not coa_row and fallback_codes:
        for code in fallback_codes:
            coa_row = conn.execute(text("""
                SELECT id, code, name
                FROM chart_of_accounts
                WHERE code = :code
                LIMIT 1
            """), {'code': code}).fetchone()
            if coa_row:
                break

    if not coa_row:
        fallback = fallback_codes[0] if fallback_codes else None
        return {'id': None, 'code': fallback, 'name': fallback}

    return {
        'id': coa_row.id,
        'code': coa_row.code,
        'name': coa_row.name
    }


def _resolve_cash_account(conn):
    for code in ('1111', '1101', '1102', '1100'):
        row = conn.execute(text("""
            SELECT id, code, name
            FROM chart_of_accounts
            WHERE code = :code
            LIMIT 1
        """), {'code': code}).fetchone()
        if row:
            return {'id': row.id, 'code': row.code, 'name': row.name}

    return {'id': None, 'code': 'CASH', 'name': 'Kas/Bank'}


def _calculate_rent_components(base_amount, calculation_method, tax_rate):
    safe_tax_rate = max(0.0, min(_to_float(tax_rate, DEFAULT_TAX_RATE), 100.0))
    base = max(0.0, _to_float(base_amount, 0.0))

    if calculation_method == 'NETTO':
        divisor = max(0.000001, 1.0 - (safe_tax_rate / 100.0))
        amount_net = base
        amount_bruto = amount_net / divisor
    else:
        amount_bruto = base
        amount_net = amount_bruto * (1.0 - (safe_tax_rate / 100.0))

    amount_tax = max(0.0, amount_bruto - amount_net)

    return {
        'amount_bruto': amount_bruto,
        'amount_net': amount_net,
        'amount_tax': amount_tax,
        'tax_rate': safe_tax_rate
    }


def _build_amortization_schedule(start_date, duration_months, monthly_amount):
    schedule = []
    if not start_date:
        return schedule

    current_year = start_date.year
    current_month = start_date.month

    for month_index in range(duration_months):
        year = current_year + ((current_month - 1 + month_index) // 12)
        month = ((current_month - 1 + month_index) % 12) + 1
        schedule.append({
            'year': year,
            'month': month,
            'amount': round(monthly_amount, 2)
        })

    return schedule


def _build_journal_preview(contract, coa_map, financials, pph42_timing, pph42_payment_date):
    payment_date = financials.get('first_payment_date') or contract.get('start_date')
    if isinstance(payment_date, str):
        payment_date = _parse_date(payment_date)

    payment_date_str = payment_date.isoformat() if isinstance(payment_date, datetime.date) else None
    deferred_tax = pph42_timing in {'next_period', 'next_year'} and financials['amount_tax'] > 0

    first_entries = []
    first_entries.append({
        'coa_id': coa_map['prepaid']['id'],
        'coa_code': coa_map['prepaid']['code'],
        'coa_name': coa_map['prepaid']['name'],
        'debit': round(financials['amount_bruto'], 2),
        'credit': 0.0
    })

    first_entries.append({
        'coa_id': coa_map['cash']['id'],
        'coa_code': coa_map['cash']['code'],
        'coa_name': coa_map['cash']['name'],
        'debit': 0.0,
        'credit': round(financials['amount_net'] if deferred_tax else financials['amount_bruto'], 2)
    })

    if deferred_tax:
        first_entries.append({
            'coa_id': coa_map['tax_payable']['id'],
            'coa_code': coa_map['tax_payable']['code'],
            'coa_name': coa_map['tax_payable']['name'],
            'debit': 0.0,
            'credit': round(financials['amount_tax'], 2)
        })

    journals = [{
        'title': 'Pengakuan Sewa Dibayar di Muka',
        'description': 'Initial recognition from rental contract',
        'transaction_date': payment_date_str,
        'entries': first_entries,
        'is_posted': False
    }]

    if deferred_tax and coa_map['tax_payable']['id']:
        tax_payment_date = _parse_date(pph42_payment_date)
        if not tax_payment_date and payment_date:
            if pph42_timing == 'next_year':
                tax_payment_date = datetime.date(payment_date.year + 1, 1, min(payment_date.day, 28))
            else:
                next_month = payment_date.month + 1
                year = payment_date.year + (1 if next_month > 12 else 0)
                month = 1 if next_month > 12 else next_month
                tax_payment_date = datetime.date(year, month, min(payment_date.day, 28))

        journals.append({
            'title': 'Pelunasan PPh 4(2)',
            'description': 'Settlement of deferred PPh 4(2)',
            'transaction_date': tax_payment_date.isoformat() if tax_payment_date else None,
            'entries': [
                {
                    'coa_id': coa_map['tax_payable']['id'],
                    'coa_code': coa_map['tax_payable']['code'],
                    'coa_name': coa_map['tax_payable']['name'],
                    'debit': round(financials['amount_tax'], 2),
                    'credit': 0.0
                },
                {
                    'coa_id': coa_map['cash']['id'],
                    'coa_code': coa_map['cash']['code'],
                    'coa_name': coa_map['cash']['name'],
                    'debit': 0.0,
                    'credit': round(financials['amount_tax'], 2)
                }
            ],
            'is_posted': False
        })

    return journals


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
        store_cols = _get_table_columns(conn, 'rental_stores')
        store_name_sql = "s.store_name" if 'store_name' in store_cols else "s.name"

        contract = conn.execute(text(f"""
            SELECT
                c.*,
                {store_name_sql} AS store_name,
                l.location_name
            FROM rental_contracts c
            LEFT JOIN rental_stores s ON c.store_id = s.id
            LEFT JOIN rental_locations l ON c.location_id = l.id
            WHERE c.id = :id
              AND (:company_id IS NULL OR c.company_id = :company_id)
            LIMIT 1
        """), {
            'id': contract_id,
            'company_id': company_id
        }).mappings().first()

        if not contract:
            return {'error': 'Rental contract not found'}

        stats = conn.execute(text("""
            SELECT
                COUNT(*) AS txn_count,
                COALESCE(SUM(ABS(amount)), 0) AS total_paid,
                MIN(txn_date) AS first_payment_date
            FROM transactions
            WHERE rental_contract_id = :contract_id
        """), {'contract_id': contract_id}).mappings().first()

        txn_count = int(stats['txn_count'] or 0)
        linked_total = _to_float(stats['total_paid'], 0.0)

        base_amount = linked_total if linked_total > 0 else _to_float(contract.get('total_amount'), 0.0)
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

        table_columns = _get_table_columns(conn, 'rental_contracts')
        notes_cfg = _extract_cfg_from_notes(contract.get('notes'))
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

        calculation_method = _normalize_calculation_method(contract_method)
        pph42_timing = _normalize_pph42_timing(contract_timing)
        pph42_rate = _to_float(contract_rate, DEFAULT_TAX_RATE)

        financials = _calculate_rent_components(base_amount, calculation_method, pph42_rate)
        financials['total_paid'] = linked_total
        financials['first_payment_date'] = stats.get('first_payment_date')

        start_date = _parse_date(contract.get('start_date'))
        end_date = _parse_date(contract.get('end_date')) or start_date
        duration_months = _month_span(start_date, end_date)
        monthly_amount = round(financials['amount_bruto'] / max(duration_months, 1), 2)

        prepaid_coa = _resolve_coa_by_setting(conn, company_id, 'prepaid_prepaid_asset_coa', ['1135', '1421'])
        expense_coa = _resolve_coa_by_setting(conn, company_id, 'prepaid_rent_expense_coa', ['5105', '5315'])
        tax_coa = _resolve_coa_by_setting(conn, company_id, 'prepaid_tax_payable_coa', ['2141', '2191'])
        cash_coa = _resolve_cash_account(conn)

        prepaid_table_columns = _get_table_columns(conn, 'prepaid_expenses')

        existing_prepaid = None
        if 'contract_id' in prepaid_table_columns:
            existing_prepaid = conn.execute(text("""
                SELECT *
                FROM prepaid_expenses
                WHERE contract_id = :contract_id
                ORDER BY updated_at DESC
                LIMIT 1
            """), {'contract_id': contract_id}).mappings().first()

        if not existing_prepaid and contract.get('prepaid_expense_id'):
            existing_prepaid = conn.execute(text("""
                SELECT *
                FROM prepaid_expenses
                WHERE id = :id
                LIMIT 1
            """), {'id': contract['prepaid_expense_id']}).mappings().first()

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
                conn.execute(text(f"""
                    UPDATE prepaid_expenses
                    SET {set_clause}
                    WHERE id = :id
                """), payload)
                prepaid_was_created = False
                prepaid_was_updated = True
            else:
                columns_sql = ', '.join(insert_columns)
                values_sql = ', '.join(f":{column}" for column in insert_columns)
                conn.execute(text(f"""
                    INSERT INTO prepaid_expenses ({columns_sql})
                    VALUES ({values_sql})
                """), payload)
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
                contract_updates['pph42_payment_date'] = _parse_date(contract_payment_date)
                update_fields.append('pph42_payment_date = :pph42_payment_date')

            if update_fields:
                update_sql = ', '.join(update_fields)
                conn.execute(text(f"""
                    UPDATE rental_contracts
                    SET {update_sql}
                    WHERE id = :id
                """), contract_updates)

        coa_map = {
            'prepaid': prepaid_coa,
            'expense': expense_coa,
            'tax_payable': tax_coa,
            'cash': cash_coa
        }

        journals = _build_journal_preview(
            contract=contract,
            coa_map=coa_map,
            financials=financials,
            pph42_timing=pph42_timing,
            pph42_payment_date=contract_payment_date
        )
        amortization_schedule = _build_amortization_schedule(start_date, duration_months, monthly_amount)

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
