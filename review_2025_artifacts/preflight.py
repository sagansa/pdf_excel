# -*- coding: utf-8 -*-
"""Preflight baca-saja: verifikasi MySQL lokal esta hidup & cakupan data 2025."""
import json
import sys

import pymysql

CONN = dict(host="127.0.0.1", port=8889, user="root", password="root", database="esta")

QUERIES = {
    "tables": "SHOW TABLES",
    "txn_count": "SELECT COUNT(*) AS n FROM transactions",
    "txn_date_range": "SELECT MIN(txn_date) AS lo, MAX(txn_date) AS hi FROM transactions",
    "txn_by_year": (
        "SELECT YEAR(txn_date) AS yr, COUNT(*) AS n, "
        "SUM(CASE WHEN mark_id IS NULL THEN 1 ELSE 0 END) AS no_mark, "
        "SUM(CASE WHEN company_id IS NULL THEN 1 ELSE 0 END) AS no_company "
        "FROM transactions GROUP BY YEAR(txn_date) ORDER BY yr"
    ),
    "companies": "SELECT id, name FROM companies",
    "coa_count": "SELECT COUNT(*) AS n FROM chart_of_accounts",
    "marks_count": "SELECT COUNT(*) AS n FROM marks",
    "marks_unmapped": (
        "SELECT COUNT(*) AS n FROM marks m "
        "WHERE NOT EXISTS (SELECT 1 FROM mark_coa_mapping mm WHERE mm.mark_id = m.id)"
    ),
    "dup_file_hash": (
        "SELECT file_hash, COUNT(*) AS n FROM transactions "
        "WHERE file_hash IS NOT NULL GROUP BY file_hash HAVING n > 1 LIMIT 10"
    ),
    "db_cr_values": "SELECT db_cr, COUNT(*) AS n FROM transactions GROUP BY db_cr",
}


def rows_to_dicts(cursor):
    return [dict(zip([c[0] for c in cursor.description], row)) for row in cursor.fetchall()]


def default(o):
    import datetime
    import decimal

    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, decimal.Decimal):
        return float(o)
    return str(o)


def main():
    out = {}
    try:
        conn = pymysql.connect(**CONN)
    except Exception as exc:  # pragma: no cover
        print(json.dumps({"error": f"connect failed: {exc}"}, indent=2))
        sys.exit(2)

    with conn.cursor() as cur:
        for key, sql in QUERIES.items():
            try:
                cur.execute(sql)
                out[key] = rows_to_dicts(cur)
            except Exception as exc:
                out[key] = [{"error": str(exc)}]
    conn.close()

    print(json.dumps(out, indent=2, default=default, ensure_ascii=False))


if __name__ == "__main__":
    main()
