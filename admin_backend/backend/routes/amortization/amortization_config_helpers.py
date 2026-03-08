import json
from copy import deepcopy

from backend.routes.accounting_utils import serialize_row_values
from backend.routes.route_utils import _parse_bool


DEFAULT_AMORTIZATION_SETTINGS = {
    'default_asset_useful_life': 5,
    'default_amortization_rate': 20.0,
    'allow_partial_year': True,
    'accumulated_depreciation_coa_codes': {
        'Building': '1524',
        'Tangible': '1530',
        'LandRights': '1534',
        'Intangible': '1601'
    },
    'prepaid_prepaid_asset_coa': '1135',
    'prepaid_rent_expense_coa': '5315',
    'prepaid_tax_payable_coa': '2191',
    'rental_cash_coa': '1101',
}


def _parse_setting_value(setting_type, raw_value, json_default):
    if setting_type == 'boolean':
        return str(raw_value).lower() == 'true'
    if setting_type == 'json':
        try:
            return json.loads(raw_value)
        except Exception:
            return json_default
    if setting_type == 'number':
        try:
            return float(raw_value)
        except Exception:
            return 0
    return raw_value


def serialize_mapping_row(row_dict):
    serialized = serialize_row_values(row_dict)
    serialized['is_deductible_50_percent'] = _parse_bool(serialized.get('is_deductible_50_percent'))
    return serialized


def merge_asset_groups(rows, company_id):
    groups = []
    merged_by_key = {}
    for row in rows:
        group = serialize_row_values(row._mapping)
        if company_id:
            merge_key = f"{group.get('asset_type')}::{group.get('group_number')}"
            existing = merged_by_key.get(merge_key)
            if existing is None or (group.get('company_id') and not existing.get('company_id')):
                merged_by_key[merge_key] = group
        else:
            groups.append(group)

    if company_id:
        return sorted(
            merged_by_key.values(),
            key=lambda g: (str(g.get('asset_type') or ''), int(g.get('group_number') or 0))
        )
    return groups


def parse_amortization_settings(rows):
    settings = deepcopy(DEFAULT_AMORTIZATION_SETTINGS)

    for row in rows:
        settings[row.setting_name] = _parse_setting_value(
            row.setting_type,
            row.setting_value,
            {},
        )

    return settings


def merge_settings_payload(rows, payload):
    existing_settings = {}
    for row in rows:
        existing_settings[row.setting_name] = _parse_setting_value(
            row.setting_type,
            row.setting_value,
            [],
        )

    merged_settings = deepcopy(DEFAULT_AMORTIZATION_SETTINGS)
    merged_settings.update(existing_settings)
    for key in DEFAULT_AMORTIZATION_SETTINGS:
        if key in payload:
            merged_settings[key] = payload.get(key)
    return merged_settings


def build_settings_to_save(merged_settings):
    return [
        ('default_asset_useful_life', str(merged_settings.get('default_asset_useful_life', 5)), 'number'),
        ('default_amortization_rate', str(merged_settings.get('default_amortization_rate', 20.0)), 'number'),
        ('allow_partial_year', str(bool(merged_settings.get('allow_partial_year', True))).lower(), 'boolean'),
        ('accumulated_depreciation_coa_codes', json.dumps(merged_settings.get('accumulated_depreciation_coa_codes', DEFAULT_AMORTIZATION_SETTINGS['accumulated_depreciation_coa_codes'])), 'json'),
        ('prepaid_prepaid_asset_coa', str(merged_settings.get('prepaid_prepaid_asset_coa', '1135')), 'text'),
        ('prepaid_rent_expense_coa', str(merged_settings.get('prepaid_rent_expense_coa', '5315')), 'text'),
        ('prepaid_tax_payable_coa', str(merged_settings.get('prepaid_tax_payable_coa', '2191')), 'text'),
        ('rental_cash_coa', str(merged_settings.get('rental_cash_coa', '1101')), 'text'),
    ]
