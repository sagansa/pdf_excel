import datetime

from backend.services.rental_financials import parse_date


def build_journal_preview(contract, coa_map, financials, pph42_timing, pph42_payment_date, amortization_schedule=None):
    payment_date = financials.get('first_payment_date') or contract.get('start_date')
    if isinstance(payment_date, str):
        payment_date = parse_date(payment_date)

    payment_date_str = payment_date.isoformat() if isinstance(payment_date, datetime.date) else None
    deferred_tax = pph42_timing in {'next_period', 'next_year'} and financials['amount_tax'] > 0

    first_entries = [{
        'coa_id': coa_map['prepaid']['id'],
        'coa_code': coa_map['prepaid']['code'],
        'coa_name': coa_map['prepaid']['name'],
        'debit': round(financials['amount_bruto'], 2),
        'credit': 0.0,
    }, {
        'coa_id': coa_map['cash']['id'],
        'coa_code': coa_map['cash']['code'],
        'coa_name': coa_map['cash']['name'],
        'debit': 0.0,
        'credit': round(financials['amount_net'] if deferred_tax else financials['amount_bruto'], 2),
    }]

    if deferred_tax:
        first_entries.append({
            'coa_id': coa_map['tax_payable']['id'],
            'coa_code': coa_map['tax_payable']['code'],
            'coa_name': coa_map['tax_payable']['name'],
            'debit': 0.0,
            'credit': round(financials['amount_tax'], 2),
        })

    journals = [{
        'title': 'Pengakuan Sewa Dibayar di Muka',
        'description': 'Initial recognition from rental contract',
        'transaction_date': payment_date_str,
        'entries': first_entries,
        'is_posted': False,
    }]

    if amortization_schedule and payment_date:
        current_year = payment_date.year
        for item in amortization_schedule:
            if item['year'] == current_year:
                try:
                    next_month = (
                        datetime.date(item['year'], item['month'] + 1, 1)
                        if item['month'] < 12
                        else datetime.date(item['year'] + 1, 1, 1)
                    )
                    txn_date = next_month - datetime.timedelta(days=1)
                except Exception:
                    txn_date = datetime.date(item['year'], item['month'], 28)

                journals.append({
                    'title': f"Amortisasi Sewa - {item['year']}/{item['month']:02d}",
                    'description': f"Monthly proportional rent expense for {item['year']}-{item['month']:02d}",
                    'transaction_date': txn_date.isoformat(),
                    'entries': [
                        {
                            'coa_id': coa_map['expense']['id'],
                            'coa_code': coa_map['expense']['code'],
                            'coa_name': coa_map['expense']['name'],
                            'debit': round(item['amount'], 2),
                            'credit': 0.0,
                        },
                        {
                            'coa_id': coa_map['prepaid']['id'],
                            'coa_code': coa_map['prepaid']['code'],
                            'coa_name': coa_map['prepaid']['name'],
                            'debit': 0.0,
                            'credit': round(item['amount'], 2),
                        },
                    ],
                    'is_posted': False,
                })

    if deferred_tax and coa_map['tax_payable']['id']:
        tax_payment_date = parse_date(pph42_payment_date)
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
                    'credit': 0.0,
                },
                {
                    'coa_id': coa_map['cash']['id'],
                    'coa_code': coa_map['cash']['code'],
                    'coa_name': coa_map['cash']['name'],
                    'debit': 0.0,
                    'credit': round(financials['amount_tax'], 2),
                },
            ],
            'is_posted': False,
        })

    return journals
