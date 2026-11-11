"""Read-only stub API for visual review of the Marks page redesign.

Serves the handful of endpoints the SPA needs to render /marks with sample
data. Runs on :5001 (the Vite proxy target). Never touches real data.
"""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

MARKS = [
    {
        "id": 1, "internal_report": "Penjualan Produk", "personal_use": "Omzet Harian",
        "is_coretax": True, "is_asset": False, "is_service": False,
        "is_salary_component": False, "is_rental": False, "fiscal_category": None,
        "mappings_real": [
            {"coa_id": 41, "code": "4-1000", "name": "Pendapatan Usaha", "type": "CREDIT"},
            {"coa_id": 1, "code": "1-1100", "name": "Kas", "type": "DEBIT"},
        ],
        "mappings_coretax": [{"coa_id": 41, "code": "4-1000", "name": "Pendapatan Usaha", "type": "CREDIT"}],
    },
    {
        "id": 2, "internal_report": "Pembelian Bahan Baku", "personal_use": "Belanja Bahan",
        "is_coretax": True, "is_asset": False, "is_service": False,
        "is_salary_component": False, "is_rental": False, "fiscal_category": "DEDUCTIBLE",
        "mappings_real": [
            {"coa_id": 12, "code": "1-3100", "name": "Persediaan Bahan", "type": "DEBIT"},
            {"coa_id": 21, "code": "2-1100", "name": "Utang Usaha", "type": "CREDIT"},
        ],
        "mappings_coretax": [{"coa_id": 12, "code": "1-3100", "name": "Persediaan Bahan", "type": "DEBIT"}],
    },
    {
        "id": 3, "internal_report": "Gaji & Tunjangan Karyawan", "personal_use": "Gaji Tim",
        "is_coretax": True, "is_asset": False, "is_service": False,
        "is_salary_component": True, "is_rental": False, "fiscal_category": "DEDUCTIBLE",
        "mappings_real": [
            {"coa_id": 61, "code": "6-1100", "name": "Beban Gaji", "type": "DEBIT"},
            {"coa_id": 22, "code": "2-1200", "name": "Utang Gaji", "type": "CREDIT"},
        ],
        "mappings_coretax": [{"coa_id": 61, "code": "6-1100", "name": "Beban Gaji", "type": "DEBIT"}],
    },
    {
        "id": 4, "internal_report": "Sewa Tempat Usaha", "personal_use": "Sewa Kantor",
        "is_coretax": True, "is_asset": False, "is_service": False,
        "is_salary_component": False, "is_rental": True, "fiscal_category": "DEDUCTIBLE",
        "mappings_real": [
            {"coa_id": 62, "code": "6-2100", "name": "Beban Sewa", "type": "DEBIT"},
            {"coa_id": 1, "code": "1-1100", "name": "Kas", "type": "CREDIT"},
        ],
        "mappings_coretax": [{"coa_id": 62, "code": "6-2100", "name": "Beban Sewa", "type": "DEBIT"}],
    },
    {
        "id": 5, "internal_report": "Iklan Digital (Meta & Google)", "personal_use": "Biaya Iklan",
        "is_coretax": True, "is_asset": False, "is_service": False,
        "is_salary_component": False, "is_rental": False, "fiscal_category": "DEDUCTIBLE",
        "mappings_real": [{"coa_id": 63, "code": "6-3100", "name": "Beban Pemasaran", "type": "DEBIT"}],
        "mappings_coretax": [{"coa_id": 63, "code": "6-3100", "name": "Beban Pemasaran", "type": "DEBIT"}],
    },
    {
        "id": 6, "internal_report": "Fee Marketplace & Payment Gateway", "personal_use": "Biaya Admin Marketplace",
        "is_coretax": True, "is_asset": False, "is_service": False,
        "is_salary_component": False, "is_rental": False, "fiscal_category": "DEDUCTIBLE",
        "mappings_real": [{"coa_id": 64, "code": "6-3200", "name": "Beban Admin", "type": "DEBIT"}],
        "mappings_coretax": [{"coa_id": 64, "code": "6-3200", "name": "Beban Admin", "type": "DEBIT"}],
    },
    {
        "id": 7, "internal_report": "Pembelian Peralatan", "personal_use": "Mesin Espresso",
        "is_coretax": False, "is_asset": True, "is_service": False,
        "is_salary_component": False, "is_rental": False, "fiscal_category": None,
        "mappings_real": [{"coa_id": 15, "code": "1-2400", "name": "Peralatan Dapur", "type": "DEBIT"}],
        "mappings_coretax": [],
    },
    {
        "id": 8, "internal_report": "Konsumsi Kantor", "personal_use": "Snack Tim",
        "is_coretax": False, "is_asset": False, "is_service": False,
        "is_salary_component": False, "is_rental": False, "fiscal_category": None,
        "mappings_real": [], "mappings_coretax": [],
    },
]


COA = [
    {"id": 1, "code": "1-1100", "name": "Kas", "category": "ASSET"},
    {"id": 12, "code": "1-3100", "name": "Persediaan Bahan", "category": "ASSET"},
    {"id": 15, "code": "1-2400", "name": "Peralatan Dapur", "category": "ASSET"},
    {"id": 21, "code": "2-1100", "name": "Utang Usaha", "category": "LIABILITY"},
    {"id": 22, "code": "2-1200", "name": "Utang Gaji", "category": "LIABILITY"},
    {"id": 41, "code": "4-1000", "name": "Pendapatan Usaha", "category": "REVENUE"},
    {"id": 61, "code": "6-1100", "name": "Beban Gaji", "category": "EXPENSE"},
    {"id": 62, "code": "6-2100", "name": "Beban Sewa", "category": "EXPENSE"},
    {"id": 63, "code": "6-3100", "name": "Beban Pemasaran", "category": "EXPENSE"},
    {"id": 64, "code": "6-3200", "name": "Beban Admin", "category": "EXPENSE"},
]

SAMPLE_MAPPINGS = {
    (3, "real"): [
        {"id": 301, "coa_id": 61, "code": "6-1100", "name": "Beban Gaji", "mapping_type": "DEBIT", "report_type": "real", "category": "EXPENSE", "notes": "Gaji bulanan tim produksi"},
        {"id": 302, "coa_id": 22, "code": "2-1200", "name": "Utang Gaji", "mapping_type": "CREDIT", "report_type": "real", "category": "LIABILITY", "notes": None},
    ],
    (3, "coretax"): [
        {"id": 311, "coa_id": 61, "code": "6-1100", "name": "Beban Gaji", "mapping_type": "DEBIT", "report_type": "coretax", "category": "EXPENSE", "notes": None},
    ],
    (4, "real"): [
        {"id": 401, "coa_id": 62, "code": "6-2100", "name": "Beban Sewa", "mapping_type": "DEBIT", "report_type": "real", "category": "EXPENSE", "notes": None},
        {"id": 402, "coa_id": 1, "code": "1-1100", "name": "Kas", "mapping_type": "CREDIT", "report_type": "real", "category": "ASSET", "notes": None},
    ],
    (4, "coretax"): [
        {"id": 411, "coa_id": 62, "code": "6-2100", "name": "Beban Sewa", "mapping_type": "DEBIT", "report_type": "coretax", "category": "EXPENSE", "notes": None},
    ],
}


TRIAL_BALANCE_ROWS = [
    {"coa_code": "1101", "coa_name": "Kas dan Setara Kas", "coa_category": "ASSET", "opening_debit": 0, "opening_credit": 0, "period_debit": 271394669.12413838, "period_credit": 124138382.47147256, "closing_debit": 147256286.65, "closing_credit": 0},
    {"coa_code": "1529", "coa_name": "Aset Tetap Lainnya", "coa_category": "ASSET", "opening_debit": 0, "opening_credit": 0, "period_debit": 9810268, "period_credit": 0, "closing_debit": 9810268, "closing_credit": 0},
    {"coa_code": "4002", "coa_name": "Penjualan Domestik", "coa_category": "REVENUE", "opening_debit": 0, "opening_credit": 0, "period_debit": 0, "period_credit": 271394669.12, "closing_debit": 0, "closing_credit": 271394669.12},
    {"coa_code": "4011", "coa_name": "Retur Penjualan", "coa_category": "REVENUE", "opening_debit": 0, "opening_credit": 0, "period_debit": 320000, "period_credit": 0, "closing_debit": 320000, "closing_credit": 0},
    {"coa_code": "5001", "coa_name": "Pembelian", "coa_category": "EXPENSE", "opening_debit": 0, "opening_credit": 0, "period_debit": 28856287, "period_credit": 0, "closing_debit": 28856287, "closing_credit": 0},
    {"coa_code": "5311", "coa_name": "Gaji, Tunjangan, Bonus, Honorarium, THR, dsb", "coa_category": "EXPENSE", "opening_debit": 0, "opening_credit": 0, "period_debit": 42946396, "period_credit": 0, "closing_debit": 42946396, "closing_credit": 0},
    {"coa_code": "5322", "coa_name": "Beban Umum dan Administrasi", "coa_category": "EXPENSE", "opening_debit": 0, "opening_credit": 0, "period_debit": 1520964.47, "period_credit": 0, "closing_debit": 1520964.47, "closing_credit": 0},
]

TRIAL_BALANCE_TOTALS = {
    "opening_debit": 0, "opening_credit": 0,
    "period_debit": 395533051.47, "period_credit": 395533051.47,
    "closing_debit": 271394669.12, "closing_credit": 271394669.12,
}


class Handler(BaseHTTPRequestHandler):
    def _match_mappings(self):
        for (mark_id, report_type), items in SAMPLE_MAPPINGS.items():
            if f"/api/marks/{mark_id}/coa-mappings" in self.path:
                if f"report_type={report_type}" in self.path:
                    return items
        return []
    def _send(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/auth/me"):
            self._send({"user": {"id": 1, "name": "Reviewer", "email": "review@local.test"}})
        elif self.path.startswith("/api/reports/trial-balance"):
            self._send({"success": True, "data": {
                "is_balanced": True,
                "rows": TRIAL_BALANCE_ROWS,
                "totals": TRIAL_BALANCE_TOTALS,
            }})
        elif self.path.startswith("/api/companies"):
            self._send({"companies": []})
        elif "/coa-mappings" in self.path:
            self._send({"mappings": self._match_mappings()})
        elif self.path.startswith("/api/marks"):
            self._send({"marks": MARKS})
        elif self.path.startswith("/api/coa"):
            self._send({"coa": COA})
        else:
            self._send({"ok": True})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        if self.path.startswith("/api/auth/login"):
            self._send({"user": {"id": 1, "name": "Reviewer", "email": "review@local.test"}})
        else:
            self._send({"ok": True})

    def do_PUT(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self._send({"ok": True})

    def do_DELETE(self):
        self._send({"ok": True})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 5001), Handler).serve_forever()
