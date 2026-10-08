import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import menu  # noqa: E402


def test_long_digit_lines_parse_quickly():
    lines = [
        "Ayran " + "1234567890" * 15,
        "Köfte " + "12 34 56 " * 40 + "x",
        "a" + "1.234,56 " * 17 + "!",
        "a" + "1.234,56 " * 17 + "x 5",
        "a" + "1.234,56 x " * 13 + "5",
        "Çay " + "1" * 150 + " TL x",
    ]
    t = time.monotonic()
    for line in lines:
        menu.split_item(menu.clean_line(line))
    assert time.monotonic() - t < 1.0


def test_prices_still_split_after_fix():
    assert menu.split_item("KIYMALI PİDE 1,5 240,00 TL") == ("KIYMALI PİDE 1,5", 240.0)
    assert menu.split_item("Kuzu şiş 1 kg 1.800 TL") == ("Kuzu şiş 1 kg", 1800.0)
    assert menu.split_item("Çay 2025 15 2026 20") is None or menu.split_item("Çay 2025 15 2026 20")[1] == 20.0
