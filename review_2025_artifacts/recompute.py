# -*- coding: utf-8 -*-
"""Rekomputasi independen FY2025 dari tabel mentah esta (SELECT-only).

Menghitung ulang tanpa memakai kode engine:
  R1  gerakan kas mentah (net DB-CR) — 3 varian basis
  R2  saldo per COA (pseudo-TB): pembuka, mutasi FY2025, penutup
  R3  komponen laba rugi versi buku besar
  R4  roll-forward ekuitas (modal + laba ditahan historis + NI 2025)
  R5  jurnal manual (bank_code='MANUAL') — materialitas
  R6  pemicu 'unclassified' arus kas (txn tanpa COA efektif)
  R7  mark dengan mapping ganda (risiko ledakan baris)
Output: recompute_results.json, pseudo_tb_<scope>.csv, is_recompute_<scope>.csv
"""
import csv
import json
from pathlib import Path

import pymysql

OUT = Path("/Users/dityo/Codings/esta/review_2025_artifacts")
CONN = dict(host="127.0.0.1", port=8889, user="root", password="root", database="esta", cursorclass=pymysql.cursors.DictCursor)

SCOPES = {
    "all": None,
    "sagansa_eng": "40e70c5f-43ef-49aa-b73e-7f83d326b301",
    "asa_pangan": "8ab69d4a-e591-4f05-909e-25ff12352efb",
}

# Fragment semantik (implementasi independen dari report_sql_fragments.py)
SIDE = """
CASE WHEN UPPER(TRIM(COALESCE(t.db_cr,''))) IN ('DB','DEBIT','D','DE') THEN 'DB'
     WHEN UPPER(TRIM(COALESCE(t.db_cr,''))) IN ('CR','CREDIT','K','KREDIT') THEN 'CR'
     ELSE NULL END
"""
DIRECT_COA = "NULLIF(TRIM(CAST(t.coa_id AS CHAR)),'')"
MAP_JOIN = """
LEFT JOIN mark_coa_mapping mcm
  ON mcm.mark_id = t.mark_id
 AND LOWER(COALESCE(NULLIF(TRIM(mcm.report_type),''),'real')) = 'real'
"""
EFF_COA = f"COALESCE({DIRECT_COA}, mcm.coa_id)"
EFF_MAP_TYPE = f"CASE WHEN {DIRECT_COA} IS NOT NULL THEN {SIDE} ELSE mcm.mapping_type END"
NAT_DIR = "NULLIF(UPPER(TRIM(m.natural_direction)),'')"
FLIP = f"""
CASE WHEN {NAT_DIR} IS NOT NULL AND {SIDE} IS NOT NULL
          AND (({NAT_DIR}='DB' AND {SIDE}='CR') OR ({NAT_DIR}='CR' AND {SIDE}='DB'))
     THEN -1 ELSE 1 END
"""
SIGNED = f"""
(CASE WHEN {EFF_MAP_TYPE}='DEBIT' THEN t.amount
      WHEN {EFF_MAP_TYPE}='CREDIT' THEN -t.amount
      ELSE 0 END) * ({FLIP})
"""
PARENT_EXCL = """
AND NOT EXISTS (SELECT 1 FROM transactions tc
                WHERE tc.parent_id = t.id
                  AND NULLIF(TRIM(COALESCE(tc.mark_id,'')),'') IS NOT NULL)
"""


def scope_sql(cid):
    return "AND (%s IS NULL OR t.company_id = %%s)" % ("NULL" if cid is None else "NULL")


def q(cur, sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()


def rows(cur, sql, params=None):
    cur.execute(sql, params or ())
    return cur.fetchall()


def main():
    conn = pymysql.connect(**CONN)
    cur = conn.cursor()
    out = {}

    for scope, cid in SCOPES.items():
        comp = [cid] if cid else [None]
        S = {}
        cid_filter = "AND (:cid IS NULL OR t.company_id = :cid)"
        # MySQL tanpa named param di pymysql -> pakai format
        cid_where = "AND (%s)" % ("1=1" if cid is None else "t.company_id = %s")

        # ---------- R1: kas mentah, 3 basis ----------
        bases = {
            "semua_baris": "",
            "tanpa_manual": "AND UPPER(TRIM(COALESCE(t.bank_code,''))) != 'MANUAL'",
            "basis_engine": PARENT_EXCL,  # engine: exclude split-parent, manual child ikut
        }
        r1 = {}
        for bname, extra in bases.items():
            sql = f"""
                SELECT
                  SUM(CASE WHEN t.txn_date < '2025-01-01' THEN IF(t.db_cr='DB', t.amount, -t.amount) ELSE 0 END) AS opening,
                  SUM(CASE WHEN t.txn_date BETWEEN '2025-01-01' AND '2025-12-31' THEN IF(t.db_cr='DB', t.amount, -t.amount) ELSE 0 END) AS fy2025,
                  SUM(CASE WHEN t.txn_date <= '2025-12-31' THEN IF(t.db_cr='DB', t.amount, -t.amount) ELSE 0 END) AS closing
                FROM transactions t WHERE 1=1 {cid_where} {extra}
            """
            params = [cid] if cid else []
            r = rows(cur, sql, params)[0]
            r1[bname] = {k: float(v or 0) for k, v in r.items()}
        S["r1_kas_mentah"] = r1

        # ---------- R2: pseudo-TB per COA ----------
        params = [cid] if cid else []
        tb_sql = f"""
            SELECT coa.code, coa.name, coa.category, coa.subcategory, coa.normal_balance,
                   SUM(CASE WHEN t.txn_date <  '2025-01-01' THEN {SIGNED} ELSE 0 END) AS opening_signed,
                   SUM(CASE WHEN t.txn_date BETWEEN '2025-01-01' AND '2025-12-31' THEN {SIGNED} ELSE 0 END) AS fy2025_signed,
                   SUM(CASE WHEN t.txn_date <= '2025-12-31' THEN {SIGNED} ELSE 0 END) AS closing_signed,
                   COUNT(*) AS n_rows
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            {MAP_JOIN}
            LEFT JOIN chart_of_accounts coa ON {EFF_COA} = coa.id
            WHERE t.txn_date <= '2025-12-31' {cid_where} {PARENT_EXCL}
            GROUP BY coa.code, coa.name, coa.category, coa.subcategory, coa.normal_balance
            ORDER BY coa.code
        """
        tb = rows(cur, tb_sql, params)
        # baris tanpa COA efektif (unmapped) ditampung terpisah
        tb = [dict(r, opening_signed=float(r["opening_signed"] or 0), fy2025_signed=float(r["fy2025_signed"] or 0),
                   closing_signed=float(r["closing_signed"] or 0), n_rows=int(r["n_rows"] or 0)) for r in tb]

        # ---------- R2b: tanpa COA (unmapped) ----------
        unm_sql = f"""
            SELECT COALESCE(m.internal_report, m.personal_use, '(mark tanpa nama)') AS mark_name,
                   COUNT(*) AS n, SUM({SIGNED}) AS net_signed
            FROM transactions t
            INNER JOIN marks m ON t.mark_id = m.id
            {MAP_JOIN}
            WHERE t.txn_date BETWEEN '2025-01-01' AND '2025-12-31'
              {cid_where} {PARENT_EXCL} AND {EFF_COA} IS NULL
            GROUP BY m.id ORDER BY ABS(SUM({SIGNED})) DESC
        """
        unm = [dict(r, n=int(r["n"]), net_signed=float(r["net_signed"] or 0)) for r in rows(cur, unm_sql, params)]
        no_mark_sql = f"""
            SELECT COUNT(*) AS n, SUM(IF(t.db_cr='DB', t.amount, -t.amount)) AS net
            FROM transactions t
            WHERE t.txn_date BETWEEN '2025-01-01' AND '2025-12-31' {cid_where}
              AND t.mark_id IS NULL {PARENT_EXCL}
        """
        nm = rows(cur, no_mark_sql, params)[0]

        S["r2_unmapped"] = {"marks_tanpa_coa": unm[:15],
                            "txn_tanpa_mark": {"n": int(nm["n"] or 0), "net": float(nm["net"] or 0)}}

        # ---------- R3: laba rugi versi buku besar ----------
        def cat_total(r):
            return {c: sum(x["fy2025_signed"] for x in tb if x["category"] == c) for c in
                    ("REVENUE", "EXPENSE", "ASSET", "LIABILITY", "EQUITY")}
        cats = cat_total(tb)
        cogs = sum(x["fy2025_signed"] for x in tb
                   if x["category"] == "EXPENSE" and (x["subcategory"] or "") == "Cost of Goods Sold")
        exp_non_cogs = cats["EXPENSE"] - cogs
        # konvensi tampilan: pendapatan positif = -signed(CREDIT); beban positif = +signed(DEBIT)
        S["r3_laba_rugi_ledger"] = {
            "revenue_ledger": -cats["REVENUE"],
            "cogs_ledger": cogs,
            "expenses_non_cogs_ledger": exp_non_cogs,
            "ni_ledger": -cats["REVENUE"] - cogs - exp_non_cogs,
            "kategori_signed": cats,
        }

        # ---------- R4: roll-forward ekuitas ----------
        ic = rows(cur, """
            SELECT company_id, amount, previous_retained_earnings_amount, start_year, report_type
            FROM initial_capital_settings
        """)
        S["r4_initial_capital_settings"] = ic
        ni_hist = {}
        for yr in (2023, 2024, 2025):
            ni_sql = f"""
                SELECT -SUM(CASE WHEN coa.category='REVENUE' THEN {SIGNED} ELSE 0 END)
                       -SUM(CASE WHEN coa.category='EXPENSE' THEN {SIGNED} ELSE 0 END) AS ni_ledger
                FROM transactions t
                INNER JOIN marks m ON t.mark_id = m.id
                {MAP_JOIN}
                LEFT JOIN chart_of_accounts coa ON {EFF_COA} = coa.id
                WHERE t.txn_date BETWEEN '{yr}-01-01' AND '{yr}-12-31' {cid_where} {PARENT_EXCL}
            """
            r = rows(cur, ni_sql, params)[0]
            ni_hist[yr] = float(r["ni_ledger"] or 0)
        S["r4_ni_ledger_tahunan"] = ni_hist

        # ---------- R5: jurnal manual ----------
        man = rows(cur, f"""
            SELECT COUNT(*) AS n,
                   SUM(IF(t.db_cr='DB', t.amount, -t.amount)) AS net,
                   SUM(CASE WHEN t.parent_id IS NULL THEN 1 ELSE 0 END) AS n_parent,
                   SUM(CASE WHEN t.parent_id IS NOT NULL THEN 1 ELSE 0 END) AS n_child
            FROM transactions t
            WHERE UPPER(TRIM(COALESCE(t.bank_code,''))) = 'MANUAL'
              AND t.txn_date <= '2025-12-31' {cid_where}
        """, params)[0]
        S["r5_jurnal_manual"] = {k: (int(v or 0) if k != "net" else float(v or 0)) for k, v in man.items()}

        # ---------- R7: mark mapping ganda (real) ----------
        dupmap = rows(cur, """
            SELECT mcm.mark_id, COUNT(*) AS n_map
            FROM mark_coa_mapping mcm
            WHERE LOWER(COALESCE(NULLIF(TRIM(mcm.report_type),''),'real')) = 'real'
            GROUP BY mcm.mark_id HAVING n_map > 1 ORDER BY n_map DESC
        """)
        S["r7_mark_mapping_ganda"] = [{"mark_id": d["mark_id"], "n_map": int(d["n_map"])} for d in dupmap]

        out[scope] = S

        # CSV pseudo-TB
        with open(OUT / f"pseudo_tb_{scope}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["code", "name", "category", "subcategory", "normal_balance",
                        "opening_signed", "fy2025_mutasi_signed", "closing_signed", "n_rows"])
            for r in tb:
                w.writerow([r["code"], r["name"], r["category"], r["subcategory"], r["normal_balance"],
                            r["opening_signed"], r["fy2025_signed"], r["closing_signed"], r["n_rows"]])

    conn.close()
    (OUT / "recompute_results.json").write_text(
        json.dumps(out, indent=2, default=str, ensure_ascii=False))
    print("OK ->", OUT / "recompute_results.json")

    # ringkasan ringkas ke stdout
    for scope, S in out.items():
        print(f"\n===== {scope} =====")
        print("kas mentah:", json.dumps(S["r1_kas_mentah"], indent=1))
        print("LR ledger:", json.dumps(S["r3_laba_rugi_ledger"]["revenue_ledger"], indent=1),
              "cogs", S["r3_laba_rugi_ledger"]["cogs_ledger"],
              "exp", S["r3_laba_rugi_ledger"]["expenses_non_cogs_ledger"],
              "NI", S["r3_laba_rugi_ledger"]["ni_ledger"])
        print("NI per tahun (ledger):", S["r4_ni_ledger_tahunan"])
        print("unmapped marks FY2025:", S["r2_unmapped"]["marks_tanpa_coa"][:5])
        print("txn tanpa mark FY2025:", S["r2_unmapped"]["txn_tanpa_mark"])
        print("jurnal manual:", S["r5_jurnal_manual"])
        print("mark mapping ganda:", len(S["r7_mark_mapping_ganda"]))


if __name__ == "__main__":
    main()
