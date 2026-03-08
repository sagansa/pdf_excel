import json
from datetime import date, datetime

from backend.routes.accounting_utils import serialize_row_values


TYPE_LABELS = {
    'Tangible': 'Harta Berwujud',
    'Intangible': 'Harta Tidak Berwujud',
    'Building': 'Bangunan',
}


def as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
    return False

def load_amortization_defaults(settings_rows):
    defaults = {
        'default_rate': 20.0,
        'default_life': 5,
        'allow_partial_year': True,
    }
    for row in settings_rows:
        if row.setting_name == 'amortization_asset_marks':
            try:
                json.loads(row.setting_value)
            except Exception:
                pass
        elif row.setting_name == 'default_amortization_rate':
            try:
                defaults['default_rate'] = float(row.setting_value)
            except Exception:
                defaults['default_rate'] = 20.0
        elif row.setting_name == 'default_asset_useful_life':
            try:
                defaults['default_life'] = int(row.setting_value)
            except Exception:
                defaults['default_life'] = 5
        elif row.setting_name == 'allow_partial_year':
            defaults['allow_partial_year'] = row.setting_value.lower() == 'true'
    return defaults


def coerce_report_date(value, fallback_year):
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date()
        except Exception:
            return date(fallback_year, 1, 1)
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date(fallback_year, 1, 1)


def purchase_year_for_row(amortization_date, report_year):
    if amortization_date:
        try:
            if isinstance(amortization_date, str):
                return int(amortization_date[:4])
            return amortization_date.year
        except Exception:
            pass
    return report_year


def group_display(asset_type, group_name, useful_life_years, tarif_rate):
    type_label = TYPE_LABELS.get(asset_type or 'Tangible', asset_type or 'Tangible')
    label = f"{type_label}"
    if group_name:
        label += f" - {group_name}"
    if useful_life_years not in (None, '', 0):
        label += f" ({int(useful_life_years)} tahun)"
    else:
        label += f" ({tarif_rate}%)"
    return label


def calculate_amortization(amount, start_date_val, report_year, tarif_rate, allow_partial_year, use_half_rate):
    annual_amort_base = amount * (tarif_rate / 100)
    accum_prev = 0
    current_year_amort = 0
    acquisition_year = start_date_val.year

    for year in range(acquisition_year, report_year + 1):
        year_amort = annual_amort_base
        if year == acquisition_year:
            if allow_partial_year:
                months = 12 - start_date_val.month + 1
                year_amort = annual_amort_base * (months / 12)
            elif use_half_rate:
                year_amort = annual_amort_base * 0.5

        remaining = amount - accum_prev
        year_amort = min(year_amort, remaining)

        if year < report_year:
            accum_prev += year_amort
        else:
            current_year_amort = year_amort

    multiplier = '1'
    if report_year == acquisition_year:
        if allow_partial_year:
            months = 12 - start_date_val.month + 1
            multiplier = f"{months}/12"
        elif use_half_rate:
            multiplier = '1/2'
    elif report_year < acquisition_year:
        multiplier = '0'

    return current_year_amort, accum_prev, multiplier


def build_manual_item_payload(row_dict, report_year, allow_partial_year):
    data = serialize_row_values(
        row_dict,
        field_datetime_formats={'amortization_date': '%Y-%m-%d'},
    )
    amount = float(data.get('amount', 0))
    purchase_year = purchase_year_for_row(data.get('amortization_date'), report_year)
    if not data.get('asset_group_id') and data.get('year') != report_year:
        return None, 0.0
    if purchase_year > report_year:
        return None, 0.0

    tarif_rate = float(data.get('tarif_rate') or 20)
    if data.get('asset_group_id'):
        start_date_val = coerce_report_date(data.get('amortization_date'), report_year)
        annual_amortization, accum_prev_val, multiplier_display = calculate_amortization(
            amount, start_date_val, report_year, tarif_rate, allow_partial_year, data.get('use_half_rate')
        )
    else:
        annual_amortization = amount
        accum_prev_val = 0
        tarif_rate = 100
        multiplier_display = '-'

    asset_type = data.get('asset_type') or 'Tangible'
    data.update({
        'accumulated_depreciation_prev_year': accum_prev_val,
        'multiplier': multiplier_display,
        'annual_amortization': annual_amortization,
        'total_accumulated_depreciation': accum_prev_val + annual_amortization,
        'book_value_end_year': max(0, amount - (accum_prev_val + annual_amortization)),
        'group': group_display(asset_type, data.get('group_name'), data.get('useful_life_years'), tarif_rate),
        'rate_type': "50%" if as_bool(data.get('use_half_rate')) else "100%",
        'is_manual': bool(data.get('is_manual')),
        'is_from_ledger': False,
        'is_manual_asset': data.get('is_manual'),
        'asset_id': None,
    })
    return data, annual_amortization


def build_registered_asset_payload(row_dict, report_year, default_rate, default_life, allow_partial_year):
    data = serialize_row_values(row_dict, datetime_format='%Y-%m-%d')
    asset_type = data.get('asset_type') or 'Tangible'
    tarif_rate = data.get('tarif_rate') or default_rate
    base_amount = float(data.get('acquisition_cost', 0))
    useful_life = int(data.get('useful_life_years') or default_life)
    start_date_val = coerce_report_date(data.get('amortization_start_date') or data.get('acquisition_date'), report_year)
    current_year_amort, accum_prev, multiplier_display = calculate_amortization(
        base_amount, start_date_val, report_year, tarif_rate, allow_partial_year, data.get('use_half_rate')
    )
    data.update({
        'annual_amortization': current_year_amort,
        'accumulated_depreciation_prev_year': accum_prev,
        'total_accumulated_depreciation': accum_prev + current_year_amort,
        'book_value_end_year': max(0, base_amount - (accum_prev + current_year_amort)),
        'multiplier': multiplier_display,
        'group': group_display(asset_type, data.get('group_name'), useful_life, tarif_rate),
        'rate_type': "50%" if as_bool(data.get('use_half_rate')) else "100%",
        'is_manual': False,
        'is_from_ledger': False,
        'is_manual_asset': False,
        'amount': base_amount,
        'acquisition_cost': base_amount,
        'amortization_date': data.get('amortization_start_date') or data.get('acquisition_date'),
        'txn_date': data.get('acquisition_date'),
    })
    return data, current_year_amort, base_amount
