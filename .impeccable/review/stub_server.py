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


class Handler(BaseHTTPRequestHandler):
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
        elif self.path.startswith("/api/marks"):
            self._send({"marks": MARKS})
        elif self.path.startswith("/api/coa"):
            self._send({"coa": []})
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
