"""Smoke test del progetto, senza dipendenze esterne.

Esecuzione (dalla radice del progetto):
    python tests/run_tests.py
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "webapp"))

PASSED = 0


def check(condition: bool, label: str) -> None:
    global PASSED
    if not condition:
        raise AssertionError(f"FALLITO: {label}")
    PASSED += 1
    print(f"  ok  {label}")


def test_calendario() -> None:
    print("[calendario]")
    from liturgia_collector.calendar import LiturgicalCalendar
    calendar = LiturgicalCalendar()
    check(calendar.easter(2026) == date(2026, 4, 5), "Pasqua 2026")
    check(calendar.easter(2025) == date(2025, 4, 20), "Pasqua 2025")
    check(calendar.first_advent_sunday(2026) == date(2026, 11, 29),
          "I Avvento 2026")
    check(calendar.baptism_of_the_lord(2026) == date(2026, 1, 11),
          "Battesimo 2026")
    samples = {
        date(2026, 7, 8): ("A", "II", "Tempo Ordinario", 14),
        date(2026, 2, 18): ("A", "II", "Quaresima", 0),
        date(2026, 4, 12): ("A", "II", "Tempo di Pasqua", 2),
        date(2026, 11, 22): ("A", "II", "Tempo Ordinario", 34),
        date(2026, 11, 29): ("B", "I", "Avvento", 1),
    }
    for day, expected in samples.items():
        info = calendar.date_info(day)
        got = (info.liturgical_year, info.lectionary_cycle,
               info.season, info.season_week)
        check(got == expected, f"{day} -> {expected}")
    check(calendar.psalter_week("Tempo Ordinario", 14) == "II",
          "salterio settimana 14")
    check(calendar.psalter_week("Quaresima", 0) == "IV",
          "salterio dopo le Ceneri")


def test_cleaner() -> None:
    print("[cleaner]")
    from liturgia_collector.cleaner import HtmlCleaner
    cleaner = HtmlCleaner()
    sample = (
        "1 ant. Santa è la tua via:\nchi è grande come te, Signore?\n\n"
        "SALMO 76 Dio rinnova i prodigi\n\n"
        "Siamo tribolati (cfr. 2 Cor 4, 8).\n\n"
        "La mia voce sale a Dio; *\nla mia voce sale a Dio.\n\n"
        "1 ant. Santa è la tua via:\nchi è grande come te, Signore?\n\n"
        "2 ant. Il mio cuore esulta.\n\nSALMO 96 La gloria\n\nIl Signore regna. *\n\n"
        "3 ant. Esulti la terra.\n\nSALMO 97 Lode\n\nCantate al Signore. *"
    )
    groups = cleaner._split_psalmody(sample)
    check(len(groups) == 3, "salmodia in 3 gruppi")
    check(groups[0]["antifona"].startswith("1 ant."), "antifona nel gruppo 1")
    check("SALMO 76" in (groups[0]["sottotitolo"] or ""),
          "titolo nel sottotitolo")
    check(groups[0]["salmo"].startswith("La mia voce"), "salmo nel gruppo 1")
    check(groups[0]["sottotitolo"].count("\n") <= 1, "sottotitolo compatto")


def test_webapp() -> None:
    print("[webapp]")
    from app import create_app
    client = create_app().test_client()
    routes_ok = ("/giorno/2026-07-08", "/mese/2026/7", "/about",
                 "/proprio", "/biennale", "/login")
    for url in routes_ok:
        check(client.get(url).status_code == 200, f"GET {url}")
    check(client.get("/").status_code == 302, "GET / redirect")
    check(client.get("/giorno/1999-01-01").status_code == 404,
          "giorno inesistente -> 404")
    check(client.get("/proprio/nuovo").status_code == 302,
          "modifiche protette da login")
    page = client.get("/giorno/2026-07-08").data.decode("utf-8")
    check("css/prego.css" in page, "css estratto collegato")
    check("js/prego.js" in page, "js estratto collegato")
    check('"availableDays"' in page, "data island presente")
    giorni = client.get("/api/giorni").get_json()
    check(giorni and "2026-07-08" in giorni["giorni"], "API /api/giorni")
    check(giorni["totale"] == len(giorni["giorni"]), "totale coerente")


def test_omelia() -> None:
    print("[omelia]")
    from youtube import YouTubeClient
    client = YouTubeClient("chiave-fittizia")
    words = client._significant("MARTEDÌ DELLA XV SETTIMANA DEL TEMPO ORDINARIO")
    check("xv" in words, "numero romano conservato")
    check(client._matches(
        "Martedì della XV settimana del Tempo Ordinario - Omelia", words),
        "settimana giusta combacia")
    check(not client._matches(
        "Martedì della XIV settimana del Tempo Ordinario", words),
        "XIV non combacia con XV")
    check(not client._matches(
        "Martedì della XXV settimana del Tempo Ordinario", words),
        "XXV non combacia con XV")
    festa = "SAN BENEDETTO, ABATE, PATRONO D'EUROPA – FESTA"
    check(client._matches(
        "San Benedetto, abate, patrono d'Europa",
        client._significant(festa)),
        "virgole e grado non bloccano il match")
    core = client._RE_CORE_SPLIT.split(festa, 1)[0]
    check(client._significant(core) == ["san", "benedetto"],
          "nucleo celebrazione = San Benedetto")


def test_amministrazione() -> None:
    print("[amministrazione]")
    from downloads import DownloadStore, describe
    from app import create_app

    check(describe("Mozilla/5.0 (Linux; Android 14) Chrome/126.0 Mobile")
          == "Android · Chrome", "User-Agent Android riconosciuto")
    # Edge e Opera si dichiarano anche Chrome: vince il marcatore proprio.
    check(describe("Mozilla/5.0 (Windows NT 10.0) Chrome/126 Edg/126")
          == "Windows · Edge", "Edge non scambiato per Chrome")
    check(describe("") == "Sconosciuto", "User-Agent vuoto")

    registro = Path(__file__).resolve().parent / "_registro_di_prova.jsonl"
    registro.unlink(missing_ok=True)
    store = DownloadStore(registro)
    check(store.record("203.0.113.7", "Android Chrome/1", "Prego.apk"),
          "download registrato")
    check(store.record("203.0.113.7", "Firefox/1", "Prego.apk"),
          "secondo download registrato")
    entries = store.entries()
    check(len(entries) == 2, "due righe nel registro")
    riepilogo = DownloadStore.summary(entries)
    check(riepilogo["totale"] == 2, "totale corretto")
    check(riepilogo["indirizzi"] == 1, "indirizzi distinti contati una volta")

    # In sola lettura non deve scrivere, ma non deve nemmeno fallire.
    sola_lettura = DownloadStore(registro, read_only=True)
    check(not sola_lettura.record("198.51.100.1", "Safari", "Prego.apk"),
          "sola lettura: nessuna registrazione")
    check(len(store.entries()) == 2, "sola lettura: registro invariato")
    registro.unlink(missing_ok=True)

    client = create_app().test_client()
    check(client.get("/app").status_code == 200, "GET /app pubblica")
    check(client.get("/admin").status_code == 302, "/admin protetta da login")
    with client.session_transaction() as session:
        session["user"] = "prova"
    check(client.get("/admin").status_code == 200, "/admin con sessione")


def main() -> int:
    for test in (test_calendario, test_cleaner, test_webapp, test_omelia,
                 test_amministrazione):
        test()
    print(f"\nTutti i test superati ({PASSED} controlli).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
