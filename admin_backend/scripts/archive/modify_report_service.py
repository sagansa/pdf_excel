import re

with open('backend/services/report_service.py', 'r') as f:
    content = f.read()

# 1. Add _coretax_filter_clause below _split_parent_exclusion_clause
coretax_helper = """
def _coretax_filter_clause(report_type='real', alias='m'):
    if str(report_type).strip().lower() != 'coretax':
        return ""
    return f" AND ({alias}.tax_report IS NOT NULL AND TRIM({alias}.tax_report) != '')"
"""
if '_coretax_filter_clause' not in content:
    content = re.sub(r'(def _split_parent_exclusion_clause.*?\n        return f" AND NOT EXISTS.*?)\n\n', r'\1\n\n' + coretax_helper + '\n', content, flags=re.DOTALL)

# 2. Update signatures and queries

# fetch_balance_sheet_data
content = content.replace('def fetch_balance_sheet_data(conn, as_of_date, company_id=None):', "def fetch_balance_sheet_data(conn, as_of_date, company_id=None, report_type='real'):")
content = content.replace("split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')", "split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')\n    coretax_clause = _coretax_filter_clause(report_type, 'm')")
content = re.sub(r'({split_exclusion_clause})(.*?GROUP BY)', r'\1\n                {coretax_clause}\2', content, flags=re.DOTALL)

# fetch_income_statement_data
content = content.replace('def fetch_income_statement_data(conn, start_date, end_date, company_id=None):', "def fetch_income_statement_data(conn, start_date, end_date, company_id=None, report_type='real'):")
# In fetch_income_statement_data we need to inject coretax_clause into the main query
content = re.sub(
    r"(split_exclusion_clause = _split_parent_exclusion_clause\(conn, 't'\)\n    query = text\(f.*?WHERE t.txn_date BETWEEN :start_date AND :end_date\n          AND \(:company_id IS NULL OR t.company_id = :company_id\)\n          \{split_exclusion_clause\})",
    r"split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')\n    coretax_clause = _coretax_filter_clause(report_type, 'm')\n    query = text(f\"\"\"\n        SELECT\n            coa.code,\n            coa.name,\n            coa.category,\n            coa.subcategory,\n            SUM(\n                CASE\n                    WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'DEBIT' THEN t.amount\n                    WHEN UPPER(COALESCE(mcm.mapping_type, '')) = 'CREDIT' THEN -t.amount\n                    WHEN t.db_cr = 'DB' THEN t.amount\n                    WHEN t.db_cr = 'CR' THEN -t.amount\n                    ELSE 0\n                END\n            ) AS total_amount\n        FROM transactions t\n        INNER JOIN marks m ON t.mark_id = m.id\n        INNER JOIN mark_coa_mapping mcm ON m.id = mcm.mark_id\n        INNER JOIN chart_of_accounts coa ON mcm.coa_id = coa.id\n        WHERE t.txn_date BETWEEN :start_date AND :end_date\n          AND (:company_id IS NULL OR t.company_id = :company_id)\n          {split_exclusion_clause}\n          {coretax_clause}",
    content, count=1, flags=re.DOTALL
)

# And update the function calls inside fetch_income_statement_data
content = content.replace('_fetch_non_contract_rent_expense_items(conn, start_date, end_date, company_id)', '_fetch_non_contract_rent_expense_items(conn, start_date, end_date, company_id, report_type)')
content = content.replace('_calculate_prorated_contract_rent_expense(conn, start_date, end_date, company_id)', '_calculate_prorated_contract_rent_expense(conn, start_date, end_date, company_id, report_type)')

# _fetch_non_contract_rent_expense_items
content = content.replace('def _fetch_non_contract_rent_expense_items(conn, start_date, end_date, company_id=None):', "def _fetch_non_contract_rent_expense_items(conn, start_date, end_date, company_id=None, report_type='real'):")
content = re.sub(
    r"(contract_filter = \"AND t.rental_contract_id IS NULL\" if 'rental_contract_id' in txn_columns else \"\")(\s+split_exclusion_clause = _split_parent_exclusion_clause\(conn, 't'\))",
    r"\1\2\n    coretax_clause = _coretax_filter_clause(report_type, 'm')",
    content
)
content = content.replace('          {split_exclusion_clause}\n        GROUP BY coa.code,', '          {split_exclusion_clause}\n          {coretax_clause}\n        GROUP BY coa.code,')

# _calculate_prorated_contract_rent_expense
content = content.replace('def _calculate_prorated_contract_rent_expense(conn, start_date, end_date, company_id=None):', "def _calculate_prorated_contract_rent_expense(conn, start_date, end_date, company_id=None, report_type='real'):")
content = re.sub(
    r"(split_exclusion_clause = _split_parent_exclusion_clause\(conn, 'tpay'\))",
    r"\1\n    coretax_clause = _coretax_filter_clause(report_type, 'm')",
    content
)
# Note: For rental contracts, transactions are linked in a subquery `txn`. That subquery also needs coretax_clause if it joins `marks`.
# Wait, _calculate_prorated_contract_rent_expense does NOT join marks in the subquery initially. Let's fix that.
# Actually I'll just check if coretax_clause is needed in `_calculate_prorated_contract_rent_expense`. If a transaction doesn't have a tax_report mark, it shouldn't be counted towards the rental payment? We'll join marks m ON tpay.mark_id = m.id in the subquery.
subqueryRegex = r"SELECT\n                tpay.rental_contract_id,\n                COALESCE\(SUM\(ABS\(tpay.amount\)\), 0\) AS linked_total\n            FROM transactions tpay\n            WHERE tpay.rental_contract_id IS NOT NULL"
subqueryReplace = r"SELECT\n                tpay.rental_contract_id,\n                COALESCE(SUM(ABS(tpay.amount)), 0) AS linked_total\n            FROM transactions tpay\n            LEFT JOIN marks m ON tpay.mark_id = m.id\n            WHERE tpay.rental_contract_id IS NOT NULL\n              {coretax_clause}"
content = re.sub(subqueryRegex, subqueryReplace, content)


# fetch_monthly_revenue_data
content = content.replace('def fetch_monthly_revenue_data(conn, year, company_id=None):', "def fetch_monthly_revenue_data(conn, year, company_id=None, report_type='real'):")
content = content.replace("split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')", "split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')\n    coretax_clause = _coretax_filter_clause(report_type, 'm')")
content = content.replace('            {split_exclusion_clause}\n        GROUP BY', '            {split_exclusion_clause}\n            {coretax_clause}\n        GROUP BY')

# fetch_payroll_salary_summary_data
content = content.replace('def fetch_payroll_salary_summary_data(conn, start_date, end_date, company_id=None):', "def fetch_payroll_salary_summary_data(conn, start_date, end_date, company_id=None, report_type='real'):")
content = content.replace("split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')", "split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')\n    coretax_clause = _coretax_filter_clause(report_type, 'm')")
content = content.replace('          {split_exclusion_clause}\n        GROUP BY', '          {split_exclusion_clause}\n          {coretax_clause}\n        GROUP BY')

# fetch_cash_flow_data
content = content.replace('def fetch_cash_flow_data(conn, start_date, end_date, company_id=None):', "def fetch_cash_flow_data(conn, start_date, end_date, company_id=None, report_type='real'):")
content = content.replace("split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')", "split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')\n    coretax_clause = _coretax_filter_clause(report_type, 'm')")
content = content.replace('               AND (:company_id IS NULL OR t.company_id = :company_id)\n               {split_exclusion_clause}', '               AND (:company_id IS NULL OR t.company_id = :company_id)\n               {split_exclusion_clause}\n               {coretax_clause}')

# _calculate_service_tax_payable_as_of
content = content.replace('def _calculate_service_tax_payable_as_of(conn, as_of_date, company_id=None):', "def _calculate_service_tax_payable_as_of(conn, as_of_date, company_id=None, report_type='real'):")
content = content.replace("split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')", "split_exclusion_clause = _split_parent_exclusion_clause(conn, 't')\n    coretax_clause = _coretax_filter_clause(report_type, 'm')")
content = content.replace('          {split_exclusion_clause}\n    """)', '          {split_exclusion_clause}\n          {coretax_clause}\n    """)')

# _calculate_rental_tax_payable_as_of
content = content.replace('def _calculate_rental_tax_payable_as_of(conn, as_of_date, company_id=None):', "def _calculate_rental_tax_payable_as_of(conn, as_of_date, company_id=None, report_type='real'):")
content = content.replace("split_exclusion_clause = _split_parent_exclusion_clause(conn, 'tpay')", "split_exclusion_clause = _split_parent_exclusion_clause(conn, 'tpay')\n    coretax_clause = _coretax_filter_clause(report_type, 'm')")
subqueryRegex2 = r"FROM transactions tpay\n            WHERE tpay.rental_contract_id IS NOT NULL"
subqueryReplace2 = r"FROM transactions tpay\n            LEFT JOIN marks m ON tpay.mark_id = m.id\n            WHERE tpay.rental_contract_id IS NOT NULL\n              {coretax_clause}"
content = re.sub(subqueryRegex2, subqueryReplace2, content)

# update calls to these functions in balance_sheet
content = content.replace('_calculate_service_tax_payable_as_of(conn, as_of_date, company_id)', '_calculate_service_tax_payable_as_of(conn, as_of_date, company_id, report_type)')
content = content.replace('_calculate_rental_tax_payable_as_of(conn, as_of_date, company_id)', '_calculate_rental_tax_payable_as_of(conn, as_of_date, company_id, report_type)')
content = content.replace('fetch_income_statement_data(conn, year_start, as_of_date, company_id)', 'fetch_income_statement_data(conn, year_start, as_of_date, company_id, report_type)')


with open('backend/services/report_service.py', 'w') as f:
    f.write(content)

