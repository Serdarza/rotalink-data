import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import monitor  # noqa: E402


def place(pid, name, address, status="OPERATIONAL", types=("restaurant",)):
    return {
        "id": pid,
        "displayName": {"text": name},
        "formattedAddress": address,
        "businessStatus": status,
        "types": list(types),
    }


class FakeClient:
    def __init__(self, responses, fail=()):
        self.responses = responses
        self.fail = set(fail)
        self.calls = 0
        self.errors = 0

    def search(self, query, page_token=None):
        self.calls += 1
        if query in self.fail:
            self.errors += 1
            raise RuntimeError(query)
        return self.responses.get(query, []), None


SOSYAL = [
    {"il": "Düzce", "ilce": "Merkez", "isim": "Düzce Belediyesi Sosyal Tesisleri", "adres": "", "aciklama": ""},
    {"il": "Düzce", "ilce": "Akçakoca", "isim": "Akçakoca Belediyesi Kafe", "adres": "", "aciklama": ""},
    {"il": "Düzce", "ilce": "Merkez", "isim": "Eski Kır Lokantası", "adres": "", "aciklama": ""},
]


def test_plan_closed_removed_others_untouched(monkeypatch):
    monkeypatch.setattr(monitor, "IL_ILCE", {"Düzce": ["Akçakoca", "Merkez"]})
    client = FakeClient({
        "Düzce Belediyesi Sosyal Tesisleri Düzce": [
            place("a", "Düzce Belediyesi Sosyal Tesisleri", "Merkez/Düzce, Türkiye", "CLOSED_PERMANENTLY"),
        ],
        "Akçakoca Belediyesi Kafe Düzce": [
            place("b", "Akçakoca Belediyesi Kafe", "Akçakoca/Düzce, Türkiye", "CLOSED_TEMPORARILY"),
        ],
        "Düzce belediyesi sosyal tesisleri": [
            place("c", "Çilimli Belediyesi Sosyal Tesisi", "81750 Çilimli/Düzce, Türkiye"),
            place("d", "Düzce Polis Sosyal Tesisleri", "Merkez/Düzce, Türkiye"),
            place("e", "Akçakoca Belediyesi Kafe", "Akçakoca/Düzce, Türkiye"),
            place("f", "Gölyaka Sosyal Tesis", "Ankara/Ankara, Türkiye"),
        ],
    })
    state = {}
    plan = monitor.plan_changes(SOSYAL, state, client)
    assert [r["kayit"]["isim"] for r in plan["remove"]] == ["Düzce Belediyesi Sosyal Tesisleri"]
    assert [r["isim"] for r in plan["temp_closed"]] == ["Akçakoca Belediyesi Kafe"]
    assert [r["isim"] for r in plan["not_found"]] == ["Eski Kır Lokantası"]
    assert [r["isim"] for r in plan["added"]] == ["Çilimli Belediyesi Sosyal Tesisi"]
    assert plan["added"][0]["il"] == "Düzce"
    assert state["misses"][monitor.record_key("Düzce", "Eski Kır Lokantası")] == 1


def test_generic_words_do_not_cause_false_match():
    assert monitor.similarity("Çilimli Belediyesi Sosyal Tesisi", "Düzce Belediyesi Sosyal Tesisleri") < 0.5
    assert monitor.similarity("Düzce Belediyesi Sosyal Tesisleri", "Düzce Belediyesi Sosyal Tesisi") == 1.0
    rec = {"il": "Düzce", "isim": "Düzce Belediyesi Sosyal Tesisleri"}
    closed_other = place("x", "Çilimli Belediyesi Sosyal Tesisi", "Çilimli/Düzce, Türkiye", "CLOSED_PERMANENTLY")
    assert monitor.best_match(rec, [closed_other])[0] is None


def test_apply_keeps_structure():
    data = {"geziler": [1], "sosyal": [dict(r) for r in SOSYAL]}
    plan = {"remove": [{"kayit": SOSYAL[0]}], "added": [{"il": "Düzce", "ilce": "", "isim": "Yeni", "adres": "", "aciklama": ""}]}
    removed = monitor.apply_plan(data, plan)
    assert [r["isim"] for r in removed] == [SOSYAL[0]["isim"]]
    assert [r["isim"] for r in data["sosyal"]] == [SOSYAL[1]["isim"], SOSYAL[2]["isim"], "Yeni"]
    assert data["geziler"] == [1]


def test_safety_blocks_mass_removal_and_errors():
    client = FakeClient({})
    plan = {"remove": [{}] * 6, "added": []}
    assert monitor.safety_check(plan, 100, client) is not None
    plan = {"remove": [{}] * 5, "added": []}
    assert monitor.safety_check(plan, 100, client) is None
    client.calls, client.errors = 10, 3
    assert "hata" in monitor.safety_check({"remove": [], "added": []}, 100, client)


def test_ilce_from_address(monkeypatch):
    monkeypatch.setattr(monitor, "IL_ILCE", {"Adana": ["Çukurova", "Seyhan"]})
    assert monitor.ilce_from_address("Adana", "Güzelyalı, 01170 Çukurova/Adana") == "Çukurova"
    assert monitor.ilce_from_address("Adana", "Kurttepe, 01170 Adana") == ""


def test_call_budget_monthly_and_per_run():
    assert monitor.call_budget({}, "2026-10") == (monitor.MAX_CALLS_PER_RUN, 0)
    state = {"aylik_cagri": {"2026-10": 3000}}
    assert monitor.call_budget(state, "2026-10") == (monitor.MONTHLY_CALL_CAP - 3000, 3000)
    assert monitor.call_budget({"aylik_cagri": {"2026-10": 9999}}, "2026-10")[0] == 0
    assert monitor.call_budget(state, "2026-11")[0] == monitor.MAX_CALLS_PER_RUN


def test_add_usage_accumulates_and_keeps_12_months():
    state = {"aylik_cagri": {f"2025-{m:02d}": 1 for m in range(1, 13)}}
    monitor.add_usage(state, "2026-01", 500)
    monitor.add_usage(state, "2026-01", 100)
    assert state["aylik_cagri"]["2026-01"] == 600
    assert len(state["aylik_cagri"]) == 12 and "2025-01" not in state["aylik_cagri"]


def test_full_scan_fits_per_run_cap():
    assert monitor.estimated_calls(1169) < monitor.MAX_CALLS_PER_RUN


def test_client_stops_at_budget():
    client = object.__new__(monitor.PlacesClient)
    client.max_calls, client.calls, client.errors = 2, 2, 0
    try:
        client.search("x")
    except monitor.CallBudgetExceeded:
        pass
    else:
        raise AssertionError("sınırda istek atılmamalı")
    assert client.calls == 2


def test_budget_exceeded_is_not_swallowed(monkeypatch):
    monkeypatch.setattr(monitor, "IL_ILCE", {"Düzce": ["Merkez"]})

    class Exhausted(FakeClient):
        def search(self, query, page_token=None):
            raise monitor.CallBudgetExceeded("dolu")

    try:
        monitor.plan_changes(SOSYAL[:1], {}, Exhausted({}))
    except monitor.CallBudgetExceeded:
        return
    raise AssertionError("sınır aşımı plan_changes içinde yutulmamalı")


def test_api_error_never_removes(monkeypatch):
    monkeypatch.setattr(monitor, "IL_ILCE", {"Düzce": ["Merkez"]})
    client = FakeClient({}, fail={"Düzce Belediyesi Sosyal Tesisleri Düzce"})
    plan = monitor.plan_changes(SOSYAL[:1], {}, client)
    assert plan["remove"] == [] and plan["not_found"] == []
