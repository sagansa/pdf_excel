from bank_parsers.bca_cc import _extract_statement_date, _parse_decimal

def test_dates():
    cases = [
        ("TANGGAL REKENING : 25 JAN 2026", (25, 1, 2026)),
        ("TANGGAL REKENING : 25 JAN 26", (25, 1, 2026)),
        ("Tgl. Rekening : 10 DES 25", (10, 12, 2025)),
        ("TANGGAL REKENING : 01/12/2025", (1, 12, 2025)),
        ("Some random text 2025", (None, None, 2025)),
    ]
    
    for text, expected in cases:
        result = _extract_statement_date(text)
        print(f"Input: '{text}' -> Expected: {expected}, Got: {result}")
        assert result == expected, f"Failed for {text}"

def test_decimals():
    cases = [
        ("1.000,00", "1000.00"),
        ("1,000.00", "1000.00"),
        ("45.900,00", "45900.00"),
        ("45,900.00", "45900.00"),
        ("500", "500.00"),
        ("100,25", "100.25"),
        ("100.25", "100.25"),
    ]
    for val, expected in cases:
        dec = _parse_decimal(val)
        res = format(dec, '.2f') if dec is not None else 'None'
        print(f"Input: '{val}' -> Expected: {expected}, Got: {res}")
        assert res == expected, f"Failed for {val}"

if __name__ == "__main__":
    try:
        test_dates()
        test_decimals()
        print("\nAll tests passed!")
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
