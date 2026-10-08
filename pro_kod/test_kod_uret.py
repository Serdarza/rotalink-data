import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import kod_uret  # noqa: E402


def test_normalize_and_hash_match_app():
    assert kod_uret.normalize("rl-ab2c 3d4e-fghj") == "RLAB2C3D4EFGHJ"
    assert kod_uret.code_hash("RL-AB2C-3D4E-FGHJ") == kod_uret.code_hash("rlab2c3d4efghj")
    # Uygulamadaki test/pro_gift_code_test.dart ile aynı değer.
    assert (
        kod_uret.code_hash("RL-AB2C-3D4E-FGHJ")
        == "c5df1eb90b02ab60c362a34e3aa9efdccc3889ed84ca6caff5e1247e4bff6d25"
    )


def test_new_code_format_and_entropy():
    codes = {kod_uret.new_code() for _ in range(200)}
    assert len(codes) == 200
    for c in codes:
        assert re.fullmatch(r"RL-[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}", c)


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
