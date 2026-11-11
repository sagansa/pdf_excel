# -*- coding: utf-8 -*-
"""Ekstraksi set laporan FY2025 dari service functions esta (baca-saja).

Output: review_2025_artifacts/json/*.json + ringkasan angka kunci ke stdout.
"""
import json
import sys
from pathlib import Path

REPO = Path("/Users/dityo/Codings/esta")
sys.path.insert(0, str(REPO / "admin_backend"))

from sqlalchemy import create_engine  # noqa: E402

from backend.services.reporting.report_service import (  # noqa: E402
    fetch_balance_sheet_data,
    fetch_cash_flow_data,
    fetch_income_statement_data,
)
from backend.routes.reporting.report_queries import build_marks_summary_query  # noqa: E402
from backend.routes.accounting_utils import serialize_result_rows  # noqa: E402

OUT = REPO / "review_2025_artifacts" / "json"
OUT.mkdir(parents=True, exist_ok=True)

COMPANIES = {
    "all": None,
    "sagansa_eng": "40e70c5f-43ef-49aa-b73e-7f83d326b301",
    "asa_pangan": "8ab69d4a-e591-4f05-909e-25ff12352efb",
    "not_included": "d8fc0225-feee-4afc-b6c2-3dd01b0ce067",
}


def default(o):
    import datetime
    import decimal

    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


def save(name, data):
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(data, indent=2, default=default, ensure_ascii=False))
    return path


def g(d, *keys, default=0.0):
    """Ambil nilai berantai dengan fallback."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def main():
    engine = create_engine("mysql+pymysql://root:root@127.0.0.1:8889/esta")
    summary = {}
    with engine.connect() as conn:
        for scope, cid in COMPANIES.items():
            is_data = fetch_income_statement_data(conn, "2025-01-01", "2025-12-31", company_id=cid)
            bs_data = fetch_balance_sheet_data(conn, "2025-12-31", company_id=cid)
            cf_data = fetch_cash_flow_data(conn, "2025-01-01", "2025-12-31", company_id=cid)

            save(f"is_2025_{scope}_real", is_data)
            save(f"bs_2025-12-31_{scope}_real", bs_data)
            save(f"cf_2025_{scope}_real", cf_data)

            summary[scope] = {
                "revenue": g(is_data, "total_revenue"),
                "expenses": g(is_data, "total_expenses"),
                "net_income": g(is_data, "total_revenue") - g(is_data, "total_expenses"),
                "bs_total_assets": g(bs_data, "totals", "total_assets"),
                "bs_total_liabilities": g(bs_data, "totals", "total_liabilities"),
                "bs_total_equity": g(bs_data, "totals", "total_equity"),
                "cf_opening": g(cf_data, "summary", "opening_cash"),
                "cf_closing": g(cf_data, "summary", "closing_cash"),
                "cf_recon_diff": g(cf_data, "summary", "reconciliation_difference"),
            }

        # Pendukung (unfiltered): neraca pembuka 2024 + IS/CF 2024 + marks summary 2025
        bs_open = fetch_balance_sheet_data(conn, "2024-12-31")
        save("bs_2024-12-31_all_real", bs_open)
        is_2024 = fetch_income_statement_data(conn, "2024-01-01", "2024-12-31")
        save("is_2024_all_real", is_2024)
        cf_2024 = fetch_cash_flow_data(conn, "2024-01-01", "2024-12-31")
        save("cf_2024_all_real", cf_2024)

        result = conn.execute(
            build_marks_summary_query("real"),
            {"start_date": "2025-01-01", "end_date": "2025-12-31", "company_id": None},
        )
        rows = serialize_result_rows(result)
        save("marks_summary_2025_all_real", {"rows": rows})

        # Varian coretax (pembanding PDF coretax_financial_statements_2025.pdf)
        save("is_2025_all_coretax", fetch_income_statement_data(
            conn, "2025-01-01", "2025-12-31", report_type="coretax"))
        save("bs_2025-12-31_all_coretax", fetch_balance_sheet_data(
            conn, "2025-12-31", report_type="coretax"))
        save("cf_2025_all_coretax", fetch_cash_flow_data(
            conn, "2025-01-01", "2025-12-31", report_type="coretax"))

        summary["bs_open_2024_all"] = {
            "total_assets": g(bs_open, "totals", "total_assets"),
            "total_liabilities": g(bs_open, "totals", "total_liabilities"),
            "total_equity": g(bs_open, "totals", "total_equity"),
        }
        summary["is_2024_all"] = {
            "net_income": g(is_2024, "total_revenue") - g(is_2024, "total_expenses"),
        }
        summary["cf_2024_all"] = {
            "closing": g(cf_2024, "summary", "closing_cash"),
            "recon_diff": g(cf_2024, "summary", "reconciliation_difference"),
        }

    save("summary", summary)
    print(json.dumps(summary, indent=2, default=default, ensure_ascii=False))


if __name__ == "__main__":
    main()
