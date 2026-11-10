"""Test parser BRI: angka CSV yang pandas-koerce ke float tidak boleh melipat 10x.

Bug pra-eksisting (ketemu saat E2E Fase 2): read_csv mengubah '1250000.00'
menjadi float 1250000.0 → str() → '1250000.0' → heuristik pemisah ribuan di
parse_decimal_amount membuang titik → 12500000 (10x). Kolom amount & balance
sama-sama kena.
"""

import pytest
from bank_parsers import bri


@pytest.fixture()
def bri_csv(tmp_path):
    path = tmp_path / 'bri.csv'
    path.write_text(
        'NOREK;TGL_TRAN;TGL_EFEKTIF;DESK_TRAN;REMARK_CUSTOM;MUTASI_DEBET;MUTASI_KREDIT;GLSIGN;SALDO_AKHIR_MUTASI\r\n'
        '1234567890123;05/11/2026 10:00;05/11/2026 10:00;TRF DB;;1250000.00;0;DB;9000000.00\r\n'
        '1234567890123;06/11/2026 11:00;06/11/2026 11:00;SETOR;;0;250000.00;CR;9250000.00\r\n',
        encoding='utf-8',
    )
    return str(path)


def test_amount_dan_saldo_tidak_melipat_sepuluh(bri_csv):
    df = bri.parse_statement(bri_csv)
    assert df.iloc[0]['amount'] == '1250000.00'
    assert df.iloc[0]['balance'] == '9000000.00'
    assert df.iloc[1]['amount'] == '250000.00'
    assert df.iloc[1]['balance'] == '9250000.00'


def test_format_lokal_tetap_benar(bri_csv):
    """Format Indonesia (1.250.000,00) tetap benar setelah perbaikan."""
    import pandas as pd
    df_raw = pd.read_csv(bri_csv, sep=';', dtype=str)
    # Baris format lokal: nilai string dengan titik ribuan + koma desimal.
    df_raw.loc[0, 'MUTASI_DEBET'] = '1.250.000,00'
    df_raw.loc[0, 'SALDO_AKHIR_MUTASI'] = '9.000.000,00'
    df = bri.parse_statement_from_dataframe(df_raw) if hasattr(bri, 'parse_statement_from_dataframe') \
        else _parse_with_dataframe(bri_csv, df_raw)
    assert df.iloc[0]['amount'] == '1250000.00'
    assert df.iloc[0]['balance'] == '9000000.00'


def _parse_with_dataframe(path, df_raw):
    """Helper: tulis ulang df_raw ke file agar parser membaca format lokal."""
    import pandas as pd
    df_raw.to_csv(path, sep=';', index=False)
    return bri.parse_statement(path)
