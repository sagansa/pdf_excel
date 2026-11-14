"""Konstanta HTTP keluar yang dipakai semua fetch ke API eksternal.

Cloudflare di zona sagansa.id memblokir UA default Python-urllib
(error 1010 — banned based on browser signature) sebelum request sampai ke
aplikasi superadmin, sehingga setiap request keluar wajib mengirim
User-Agent identifikasi aplikasi ini.
"""

USER_AGENT = 'StatementX/1.0 (+https://esta.sagansa.id)'
