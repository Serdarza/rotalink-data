import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kod_uret  # noqa: E402


def test_normalize_and_hash_match_app():
    assert kod_uret.normalize("ab2c-3d4e fghj-kmnp") == "AB2C3D4EFGHJKMNP"
    assert kod_uret.code_hash("AB2C-3D4E-FGHJ-KMNP") == kod_uret.code_hash("ab2c3d4efghjkmnp")
    # Uygulamadaki test/pro_gift_code_test.dart ile aynı değer.
    assert (
        kod_uret.code_hash("AB2C-3D4E-FGHJ-KMNP")
        == "2b3024260e20333fb79a0d7865feefd823576e2b74683935982e10034ae280ec"
    )


def test_new_code_format_and_entropy():
    codes = {kod_uret.new_code() for _ in range(200)}
    assert len(codes) == 200
    for c in codes:
        assert re.fullmatch(r"[2-9A-HJKMNP-Z]{4}(-[2-9A-HJKMNP-Z]{4}){3}", c)


def test_kolay_uret_flow(tmp_path, monkeypatch):
    import kolay_uret

    monkeypatch.setattr(kod_uret, "DATA", tmp_path / "pro_kodlar.json")
    monkeypatch.setattr(kod_uret, "OUT_DIR", tmp_path / "uretilen")
    monkeypatch.setattr(kolay_uret, "NOTES", tmp_path / "notlar.txt")
    calls = []
    monkeypatch.setattr(kolay_uret, "git", lambda *a: calls.append(a) or True)
    answers = iter(["3", "2", "abc", "4", "Yaz kampanyası"])
    monkeypatch.setattr("builtins.input", lambda _="": next(answers))
    assert kolay_uret.main() == 0
    notes = (tmp_path / "notlar.txt").read_text(encoding="utf-8")
    assert "YILLIK (365 gün Pro) — 4 adet" in notes and "Yaz kampanyası" in notes
    assert notes.count("Verildi:") == 4
    assert len(kod_uret.load()["kodlar"]) == 4
    assert any(c[0] == "commit" and c[-1] == "pro_kodlar.json" for c in calls)
    assert any(c[0] == "push" for c in calls)


def test_generate_and_revoke(tmp_path, monkeypatch):
    monkeypatch.setattr(kod_uret, "DATA", tmp_path / "pro_kodlar.json")
    monkeypatch.setattr(kod_uret, "OUT_DIR", tmp_path / "uretilen")
    monkeypatch.setattr(kod_uret, "ROOT", tmp_path)
    assert kod_uret.main(["uret", "--plan", "aylik", "--adet", "2"]) == 0
    data = kod_uret.load()
    assert len(data["kodlar"]) == 2
    raw = (tmp_path / "pro_kodlar.json").read_text(encoding="utf-8")
    plain = next((tmp_path / "uretilen").iterdir()).read_text(encoding="utf-8").splitlines()[1]
    assert plain not in raw and kod_uret.normalize(plain) not in raw
    assert kod_uret.main(["iptal", "--kod", plain]) == 0
    assert len(kod_uret.load()["kodlar"]) == 1
    assert kod_uret.main(["uret", "--plan", "yillik", "--kod", "YAZ2026", "--kullanim", "50"]) == 0
    entry = [k for k in kod_uret.load()["kodlar"] if k["plan"] == "yillik"][0]
    assert entry["kullanim"] == 50
