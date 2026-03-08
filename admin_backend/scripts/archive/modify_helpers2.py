import re

with open('backend/services/report_service.py', 'r') as f:
    content = f.read()

# Fix assets_query inside _calculate_dynamic_5314_total
assets_replacement = """    asset_company_clause = "AND a.company_id = :company_id" if company_id else ""
    if str(report_type).strip().lower() == 'coretax':
        coretax_assets_clause = "AND (a.tax_report IS NOT NULL AND TRIM(a.tax_report) != '')"
    else:
        coretax_assets_clause = ""
"""
content = content.replace('    asset_company_clause = "AND a.company_id = :company_id" if company_id else ""', assets_replacement)
content = content.replace('          {asset_company_clause}\n    """)', '          {asset_company_clause}\n          {coretax_assets_clause}\n    """)')

with open('backend/services/report_service.py', 'w') as f:
    f.write(content)
