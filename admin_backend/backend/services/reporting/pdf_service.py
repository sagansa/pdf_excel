import os
from collections import OrderedDict
from copy import deepcopy

from flask import current_app as app
from jinja2 import Environment, FileSystemLoader


class PdfDependencyError(RuntimeError):
    """Raised when optional PDF export dependencies are not installed."""


def _require_pisa():
    try:
        from xhtml2pdf import pisa
    except ImportError as exc:  # pragma: no cover - depends on runtime environment
        raise PdfDependencyError(
            "PDF export requires xhtml2pdf. Install backend requirements before exporting reports."
        ) from exc
    return pisa


def _require_pdf_merge_lib():
    try:
        from pypdf import PdfReader, PdfWriter
        return PdfReader, PdfWriter
    except ImportError:
        try:
            from PyPDF2 import PdfReader, PdfWriter
            return PdfReader, PdfWriter
        except ImportError as exc:  # pragma: no cover - depends on runtime environment
            raise PdfDependencyError(
                "PDF merge requires pypdf or PyPDF2. Install backend requirements before exporting reports."
            ) from exc


def format_indo_date(date_str):
    months = ['Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
    try:
        y, m, d = date_str.split('-')
        return f"{int(d)} {months[int(m)-1]} {int(y)}"
    except (AttributeError, TypeError, ValueError, IndexError):
        return date_str


def _get_template_env():
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    return Environment(loader=FileSystemLoader(template_dir))


def _write_pdf(html_content, report_filename):
    pisa = _require_pisa()
    output_dir = app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'tmp'))
    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.join(output_dir, report_filename)
    with open(pdf_path, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

    if pisa_status.err:
        raise Exception(f"Failed to generate PDF: {pisa_status.err}")

    return pdf_path


def _merge_pdfs(pdf_paths, report_filename):
    PdfReader, PdfWriter = _require_pdf_merge_lib()
    output_dir = app.config.get('UPLOAD_FOLDER', os.path.join(os.getcwd(), 'tmp'))
    os.makedirs(output_dir, exist_ok=True)

    merged_pdf_path = os.path.join(output_dir, report_filename)
    writer = PdfWriter()

    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)

    with open(merged_pdf_path, "wb") as merged_file:
        writer.write(merged_file)

    for pdf_path in pdf_paths:
        try:
            os.remove(pdf_path)
        except OSError:
            pass

    return merged_pdf_path


def generate_income_statement_pdf(report_data):
    """
    Generate a PDF from income statement data using Jinja2 and xhtml2pdf.
    """
    # 1. Setup Jinja2 environment
    env = _get_template_env()
    template = env.get_template('income_statement.html')
    
    # 1.5 Prepare custom format variables
    end_date_str = report_data.get('period', {}).get('end_date', '')
    report_data['end_date_formatted'] = format_indo_date(end_date_str) if end_date_str else ''
    
    op_expenses = []
    tax_expenses = []
    for exp in report_data.get('expenses', []):
        if str(exp.get('code', '')).startswith('549'):
            tax_expenses.append(exp)
        else:
            op_expenses.append(exp)
            
    total_op_expenses = sum(e.get('amount', 0) for e in op_expenses)
    total_tax_expenses = sum(e.get('amount', 0) for e in tax_expenses)
    
    cogs = float(report_data.get('total_cogs', 0))
    revenue = float(report_data.get('total_revenue', 0))
    gross_profit = revenue - cogs
    ebt = gross_profit - total_op_expenses
    
    report_data['op_expenses'] = op_expenses
    report_data['tax_expenses'] = tax_expenses
    report_data['total_op_expenses'] = total_op_expenses
    report_data['total_tax_expenses'] = total_tax_expenses
    report_data['gross_profit'] = gross_profit
    report_data['ebt'] = ebt

    # 2. Render HTML
    html_content = template.render(**report_data)

    # 3. Create PDF
    report_filename = f"income_statement_{report_data['period']['start_date']}.pdf"
    return _write_pdf(html_content, report_filename)


def generate_balance_sheet_pdf(report_data):
    """
    Generate a PDF from balance sheet data using Jinja2 and xhtml2pdf.
    """
    env = _get_template_env()
    template = env.get_template('balance_sheet.html')

    as_of_date = report_data.get('as_of_date', '')
    report_data['as_of_date_formatted'] = format_indo_date(as_of_date) if as_of_date else ''

    assets = report_data.get('assets', {})
    assets['current'] = [
        item for item in assets.get('current', [])
        if not item.get('hide_in_pdf')
    ]
    assets['non_current'] = [
        item for item in assets.get('non_current', [])
        if not item.get('hide_in_pdf')
    ]
    report_data['assets'] = assets
    report_data['total_current_assets'] = sum(
        item.get('amount', 0)
        for item in assets.get('current', [])
        if not item.get('exclude_from_total')
    )
    report_data['total_non_current_assets'] = sum(
        item.get('amount', 0)
        for item in assets.get('non_current', [])
        if not item.get('exclude_from_total')
    )

    liabilities = report_data.get('liabilities', {})
    equity = report_data.get('equity', {})
    report_data['total_current_liabilities'] = sum(
        item.get('amount', 0) for item in liabilities.get('current', [])
    )
    report_data['total_non_current_liabilities'] = sum(
        item.get('amount', 0) for item in liabilities.get('non_current', [])
    )
    report_data['liabilities_and_equity_difference'] = (
        float(report_data.get('total_assets', 0) or 0)
        - float(report_data.get('total_liabilities_and_equity', 0) or 0)
    )
    report_data['has_balance_difference'] = abs(report_data['liabilities_and_equity_difference']) >= 0.01
    report_data['equity_items'] = [
        item for item in equity.get('items', [])
        if (
            not item.get('hide_in_pdf')
            and not item.get('exclude_from_total')
            and not item.get('is_child_row')
        )
    ]

    html_content = template.render(**report_data)
    report_filename = f"balance_sheet_{as_of_date}.pdf"
    return _write_pdf(html_content, report_filename)


def _group_amortization_items(items):
    type_order = ['Tangible', 'Building', 'Intangible']
    labels = {
        'Tangible': 'Harta Berwujud',
        'Building': 'Bangunan',
        'Intangible': 'Harta Tidak Berwujud',
    }
    grouped = {}

    for item in items:
        asset_type = item.get('asset_type') or 'Tangible'
        group_name = item.get('group_name') or item.get('mark_name') or '-'
        if asset_type not in grouped:
            grouped[asset_type] = {}
        if group_name not in grouped[asset_type]:
            grouped[asset_type][group_name] = []
        grouped[asset_type][group_name].append(item)

    ordered = OrderedDict()
    for asset_type in type_order:
        if asset_type in grouped:
            ordered[asset_type] = {
                'label': labels.get(asset_type, asset_type),
                'groups': OrderedDict(sorted(grouped[asset_type].items(), key=lambda item: item[0])),
            }

    for asset_type, groups in grouped.items():
        if asset_type not in ordered:
            ordered[asset_type] = {
                'label': labels.get(asset_type, asset_type),
                'groups': OrderedDict(sorted(groups.items(), key=lambda item: item[0])),
            }

    return ordered


def _format_month_year(date_str):
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
    try:
        y, m, _ = str(date_str)[:10].split('-')
        return f"{months[int(m) - 1]} {y}"
    except Exception:
        return str(date_str or '-')


def generate_amortization_pdf(report_data):
    env = _get_template_env()
    template = env.get_template('amortization.html')

    items = report_data.get('items', [])
    calculated_items = [item for item in items if item.get('asset_id')]
    manual_items = [item for item in items if not item.get('asset_id')]

    report_data['calculated_items'] = calculated_items
    report_data['manual_items'] = manual_items
    report_data['grouped_calculated_items'] = _group_amortization_items(calculated_items)
    report_data['total_original_cost'] = sum(float(item.get('acquisition_cost', 0) or 0) for item in calculated_items)
    report_data['total_book_value_end'] = sum(float(item.get('book_value_end_year', 0) or 0) for item in calculated_items)
    report_data['calculated_total_amortization'] = sum(
        float(item.get('annual_amortization', 0) or 0) for item in calculated_items
    )
    report_data['manual_total_cost'] = sum(float(item.get('amount', 0) or 0) for item in manual_items)
    report_data['manual_total_accum_prev'] = sum(
        float(item.get('accumulated_depreciation_prev_year', 0) or 0) for item in manual_items
    )
    report_data['manual_total_amortization'] = sum(
        float(item.get('annual_amortization', item.get('amount', 0)) or 0) for item in manual_items
    )
    report_data['manual_total_accum_total'] = sum(
        float(item.get('total_accumulated_depreciation', item.get('amount', 0)) or 0) for item in manual_items
    )
    report_data['manual_total_book_value'] = sum(
        float(item.get('book_value_end_year', 0) or 0) for item in manual_items
    )
    report_data['grand_total_amortization'] = (
        report_data['calculated_total_amortization'] + report_data['manual_total_amortization']
    )
    report_data['grand_total_book_value'] = (
        report_data['total_book_value_end'] + report_data['manual_total_book_value']
    )
    sorted_rows = sorted(
        items,
        key=lambda item: str(
            item.get('acquisition_date')
            or item.get('txn_date')
            or item.get('amortization_date')
            or item.get('created_at')
            or ''
        ),
    )
    report_data['amortization_rows'] = []
    for index, item in enumerate(sorted_rows, start=1):
        acquisition_date = (
            item.get('acquisition_date')
            or item.get('txn_date')
            or item.get('amortization_date')
            or item.get('created_at')
        )
        original_cost = float(item.get('acquisition_cost', item.get('amount', 0)) or 0)
        depreciation_prev = float(item.get('accumulated_depreciation_prev_year', 0) or 0)
        depreciation_current = float(item.get('annual_amortization', item.get('amount', 0)) or 0)
        accumulated = float(
            item.get('total_accumulated_depreciation', depreciation_prev + depreciation_current) or 0
        )
        book_value_end = float(item.get('book_value_end_year', max(0, original_cost - accumulated)) or 0)
        report_data['amortization_rows'].append({
            'no': index,
            'asset_name': item.get('asset_name') or item.get('description') or '-',
            'asset_type': item.get('asset_type') or 'Tangible',
            'asset_type_label': {
                'Tangible': 'Harta Berwujud',
                'Intangible': 'Harta Tidak Berwujud',
                'Building': 'Bangunan',
            }.get(item.get('asset_type') or 'Tangible', item.get('asset_type') or 'Harta Berwujud'),
            'acquisition_month_year': _format_month_year(acquisition_date),
            'original_cost': original_cost,
            'depreciation_prev': depreciation_prev,
            'depreciation_current': depreciation_current,
            'accumulated': accumulated,
            'book_value_end': book_value_end,
        })
    type_order = ['Tangible', 'Intangible', 'Building']
    grouped_rows = OrderedDict()
    for asset_type in type_order:
        rows = [row for row in report_data['amortization_rows'] if row.get('asset_type') == asset_type]
        if rows:
            grouped_rows[rows[0]['asset_type_label']] = rows
    other_rows = [
        row for row in report_data['amortization_rows']
        if row.get('asset_type') not in type_order
    ]
    for row in other_rows:
        grouped_rows.setdefault(row['asset_type_label'], []).append(row)
    report_data['grouped_amortization_rows'] = grouped_rows
    report_data['sum_original_cost'] = sum(row['original_cost'] for row in report_data['amortization_rows'])
    report_data['sum_depreciation_prev'] = sum(row['depreciation_prev'] for row in report_data['amortization_rows'])
    report_data['sum_depreciation_current'] = sum(row['depreciation_current'] for row in report_data['amortization_rows'])
    report_data['sum_accumulated'] = sum(row['accumulated'] for row in report_data['amortization_rows'])
    report_data['sum_book_value_end'] = sum(row['book_value_end'] for row in report_data['amortization_rows'])
    report_data['previous_year_label'] = int(report_data.get('year', 0) or 0) - 1
    report_data['current_year_label'] = int(report_data.get('year', 0) or 0)

    html_content = template.render(**report_data)
    report_filename = f"amortization_{report_data.get('year', '')}.pdf"
    return _write_pdf(html_content, report_filename)


def generate_coretax_combined_pdf(income_statement_data, balance_sheet_data, amortization_data, report_filename):
    pdf_paths = [
        generate_income_statement_pdf(deepcopy(income_statement_data)),
        generate_balance_sheet_pdf(deepcopy(balance_sheet_data)),
        generate_amortization_pdf(deepcopy(amortization_data)),
    ]
    return _merge_pdfs(pdf_paths, report_filename)
