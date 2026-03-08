import re

with open('backend/services/report_service.py', 'r') as f:
    content = f.read()

# _calculate_dynamic_5314_total
content = content.replace('def _calculate_dynamic_5314_total(conn, start_date, company_id=None):', "def _calculate_dynamic_5314_total(conn, start_date, company_id=None, report_type='real'):")
# inject coretax into txn_query inside dynamic_5314
# find txn_company_clause = "AND t.company_id = :company_id" if company_id else ""
replacement = """    txn_company_clause = "AND t.company_id = :company_id" if company_id else ""
    coretax_clause = _coretax_filter_clause(report_type, 'm')
"""
content = content.replace('    txn_company_clause = "AND t.company_id = :company_id" if company_id else ""', replacement)
content = content.replace('          AND {txn_year_clause}\n    """)', '          AND {txn_year_clause}\n          {coretax_clause}\n    """)')

# inject coretax into manual_query. Since manual_query touches amortization_items, we need to join it to marks
# BUT amortization_items doesn't have a mark_id. It's a manual entry.
# Based on the user requirement, "Coretax" should only include items explicitly mapped to tax.
# If manual amortizations are entered, are they tax deductible? Usually yes, but the user specifies "if mapped to coretax".
# For now, to be safe and strictly adhere to "only transactions mapped to tax_report", if `report_type == 'coretax'` we might want to skip `manual_query` if it lacks a tax_report mapping, or check if `amortization_items` has a relation to `marks`.
# Wait, `marks` has a row for manual amortizations?
# Yes, migration 28 "change amortization to mark based" connects manual items to marks if done correctly, but currently `amortization_items` has NO mark_id. It is standalone.
# If report_type == 'coretax', it's safer to skip unmapped manual amortizations, OR we assume manual amortizations are always for real matching. Let's look if amortization_items has a tax_report equivalent. Let's just bypass `manual_query` if coretax for now, unless we can join it. Actually, the user requirement is "bila dimasukkan maka menjadi lebih bayar ... maka tidak semua dimasukkan ke coretax". This usually refers to expenses/revenues. Amortization is an expense. If they want to hide an asset from coretax, the acquisition transaction wouldn't have `tax_report`. If the acquisition isn't in coretax, its amortization shouldn't be either. The `txn_query` handles acquisition transactions and we just added `coretax_clause` to it. The `manual_query` is for legacy/historical assets before the system was fully used. Let's assume historical data also needs filtering. However we can't filter `amortization_items` by `tax_report` directly. We will leave `manual_query` alone for now, or clear it if it's coretax. Let's clear it if coretax to be strictly "only mapped items". But wait, the 53 million in the log was `manual_total: 50,345,697`. So manual amortization is the culprit.
# Is there a tax_report link for historical assets? Let's check `database/migrations` for amortization_items.
