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
    # pagina dei santi del giorno (data/santi/GG-MM.json)
    santi = client.get("/santi/2026-09-22")
    check(santi.status_code == 200, "GET /santi/2026-09-22")
    santi_html = santi.data.decode("utf-8")
    check("San Maurizio" in santi_html and "Altri santi e beati" in santi_html,
          "santi del 22 settembre: principale ed elenco")
    check(client.get("/santi/1999-01-01").status_code == 404,
          "santi di un giorno non raccolto -> 404")
    check('href="/santi/2026-07-08"' in page, "pulsante Santi nella pagina del giorno")
    # scheda Giorno: entrambe le fonti nella pagina (data-fonte), la
    # preferenza del dispositivo (Impostazioni) decide quale si vede;
    # i pulsanti flottanti portano la stessa etichetta della fonte
    import re as _re
    def fonti(iso):
        html = client.get(f"/giorno/{iso}").data.decode("utf-8")
        salti = {m.group(1) for m in _re.finditer(r'data-jump="(biennale|proprio|letture)"', html)}
        sezioni = set(_re.findall(r'data-key="[^"]+" data-fonte="(biennale|ufficio)"', html))
        return salti, sezioni
    salti, sezioni = fonti("2026-09-23")   # S. Pio, memoria: Biennale + Proprio, più l'Ufficio
    check(salti == {"biennale", "proprio", "letture"} and sezioni == {"biennale", "ufficio"},
          "memoria: sezioni e pulsanti di entrambe le fonti")
    salti, sezioni = fonti("2026-08-15")   # Assunzione: solo Proprio (+ Ufficio)
    check("proprio" in salti and "biennale" not in salti and sezioni == {"biennale", "ufficio"},
          "solennità: Proprio senza Biennale, Ufficio come alternativa")
    salti, sezioni = fonti("2026-04-27")   # nessuna voce del Biennale
    check(salti == {"letture"} and sezioni == {"ufficio"},
          "senza Biennale: solo l'Ufficio delle letture")
    # pannello del silenzio: prima dell'Antifona al Benedictus, tre durate
    pos_silenzio = page.find('data-key="silenzio"')
    pos_benedictus = page.find('data-key="antifona_al_benedictus"')
    check(0 < pos_silenzio < pos_benedictus,
          "pannello Silenzio prima dell'Antifona al Benedictus")
    check(all(f'data-minuti="{m}"' in page for m in (5, 10, 15))
          and 'id="silenzioPanel"' in page,
          "pannello Silenzio con 5/10/15 minuti")
    check(client.get("/impostazioni").status_code == 200, "GET /impostazioni")
    check('name="letture"' in client.get("/impostazioni").data.decode("utf-8"),
          "Impostazioni con la scelta della fonte delle letture")
    check('data-letture' in page, "preferenza letture applicata prima del rendering")
    # controllo aggiornamenti dell'app: /api/version e banner in-app
    versione = client.get("/api/version").get_json()
    check(versione and versione["versione"] and versione["versionCode"] > 0
          and versione["url"].endswith("/app/scarica"), "API /api/version")
    vecchia = client.get("/about", headers={"User-Agent": "PregoAndroid/2.09"}
                         ).data.decode("utf-8")
    check("Scarica l'aggiornamento" in vecchia and "App installata 2.09" in vecchia
          and "github.com" in vecchia,
          "app 2.09 -> banner di aggiornamento con download da host esterno")
    attuale = client.get("/about", headers={"User-Agent": f"PregoAndroid/{versione['versione']}"}
                         ).data.decode("utf-8")
    check("Scarica l'aggiornamento" not in attuale
          and f"App installata {versione['versione']}" in attuale,
          "app aggiornata -> nessun banner")
    check("Scarica l'aggiornamento" not in page, "dal sito nessun banner")
    pagina_app = client.get("/app").data.decode("utf-8")
    check(f"Prego-{versione['versione']}.apk" in pagina_app
          and f"Versione <strong>{versione['versione']}</strong>" in pagina_app,
          "pagina Scarica l'app con la versione pubblicata")
    scarica = client.get("/app/scarica")
    check(scarica.status_code == 200
          and f"Prego-{versione['versione']}.apk" in scarica.headers.get("Content-Disposition", "")
          and scarica.headers.get("Cache-Control") == "no-store",
          "download APK con nome versionato e senza cache")
    scarica.close()
    # dal sito il menu ha Scarica l'app e Accedi; dall'app Android no
    check("Scarica l'app" in page and "Accedi" in page,
          "menu del sito con Scarica l'app e Accedi")
    da_app = client.get("/giorno/2026-07-08",
                        headers={"User-Agent": "PregoAndroid/2.07"}
                        ).data.decode("utf-8")
    check("Scarica l'app" not in da_app and ">Accedi<" not in da_app,
          "menu dell'app senza Scarica l'app e Accedi")


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
    check(client.get("/admin/utenti").status_code == 302,
          "/admin/utenti protetta da login")
    with client.session_transaction() as session:
        session["user"] = "prova"
    check(client.get("/admin").status_code == 200, "/admin con sessione")
    check(client.get("/admin/utenti").status_code == 200,
          "/admin/utenti con sessione")

    # ping di avvio dell'app: validazione del corpo (senza scrivere nello store)
    from pings import clean_ping
    valido = clean_ping({"id": "0B6C4B1E-9D0D-4F1E-8A2B-0123456789AB", "versione": "2.12",
                         "versionCode": 8, "android": "14", "sdk": 34,
                         "modello": "Pixel 8", "lingua": "it-IT", "avvii": 3})
    check(valido is not None and valido["id"].islower() and valido["avvii"] == 3,
          "ping valido normalizzato")
    check(clean_ping({"id": "non-un-uuid", "versione": "2.12"}) is None,
          "ping con id non valido rifiutato")
    check(clean_ping({"id": valido["id"], "versione": "abc"}) is None,
          "ping con versione non valida rifiutato")
    check(clean_ping("stringa") is None, "ping non JSON rifiutato")
    check(client.post("/api/ping", json={"id": "x"}).status_code == 400,
          "POST /api/ping non valido -> 400")
    check(client.get("/api/ping").status_code == 405, "GET /api/ping -> 405")


def test_biennale_data() -> None:
    """Ferie a data fissa: il Biennale si trova per giorno del mese."""
    print("[biennale a data fissa]")
    import json
    import shutil
    from biennale import BiennaleStore
    from repository import LiturgiaRepository

    check(BiennaleStore.date_code("Tempo di Natale", 2, 1, "I")
          == "natale-2-gennaio-i", "codice per data con ciclo")
    check(BiennaleStore.date_code("Avvento", 17, 12, None)
          == "avvento-17-dicembre", "codice per data senza ciclo")

    cartella = Path(__file__).resolve().parent / "_biennale_di_prova"
    shutil.rmtree(cartella, ignore_errors=True)
    cartella.mkdir()
    voce = {
        "tempo_liturgico": "Tempo di Natale", "settimana_del_tempo": None,
        "giorno_settimana": None, "anno_liturgico": None,
        "ciclo_biennale": "I", "data": "02-01", "data_estesa": "2 Gennaio",
        "letture": [{"titolo": "Prima Lettura", "riferimento": "2,16-3,4",
                     "sottotitolo": "", "fonte": "Dalla lettera ai Colossesi",
                     "testo": "Fratelli...", "responsorio": ""}],
        "codice": "natale-2-gennaio-i",
    }
    (cartella / "natale-2-gennaio-i.json").write_text(
        json.dumps(voce, ensure_ascii=False), encoding="utf-8")
    store = BiennaleStore(cartella)
    repo = LiturgiaRepository(cartella, cartella, biennale_store=store)
    metadati = {"data": "2027-01-02", "tempo_liturgico": "Tempo di Natale",
                "giorno_settimana": "Sabato", "ciclo_biennale": "I"}
    trovata = repo._find_biennale(metadati)
    check(trovata is not None and trovata["codice"] == "natale-2-gennaio-i",
          "2 gennaio trovato per data, qualunque sia il giorno della settimana")
    check(repo._find_biennale({**metadati, "data": "2027-01-03"}) is None,
          "3 gennaio senza voce -> nessun risultato")
    # senza ciclo nei metadati si ripiega sulla voce generica
    (cartella / "natale-2-gennaio.json").write_text(
        json.dumps({**voce, "ciclo_biennale": None, "codice": "natale-2-gennaio"},
                   ensure_ascii=False), encoding="utf-8")
    generica = repo._find_biennale({**metadati, "ciclo_biennale": "II"})
    check(generica is not None and generica["codice"] == "natale-2-gennaio",
          "ciclo II senza voce propria -> voce senza ciclo")
    sezioni = repo._biennale_sections(trovata)
    check(sezioni and "2 Gennaio" in (sezioni[0].text or ""),
          "intestazione con la data estesa")
    # la form di modifica conserva la chiave per data
    form = {"tempo_liturgico": "Tempo di Natale", "giorno_settimana": "Sabato",
            "ciclo_biennale": "I", "data": "02-01",
            "lettura_1_riferimento": "2,16-3,4", "lettura_1_testo": "Fratelli..."}
    check(BiennaleStore.from_form(form)["codice"] == "natale-2-gennaio-i",
          "from_form conserva il codice per data")
    shutil.rmtree(cartella, ignore_errors=True)


def test_proprio_festa() -> None:
    """Il Proprio del santo entra nella scheda Giorno solo se celebrato."""
    print("[proprio nelle feste]")
    from repository import LiturgiaRepository

    cecilia = {"santo": "Santa Cecilia, vergine e martire", "letture": []}
    check(LiturgiaRepository.proprio_applies(
        cecilia, {"grado": "Memoria",
                  "celebrazione": "SANTA CECILIA, VERGINE E MARTIRE - MEMORIA"}),
        "memoria del santo -> Proprio in uso")
    check(not LiturgiaRepository.proprio_applies(
        cecilia, {"grado": "Solennità",
                  "celebrazione": "XXXIV DOMENICA - SOLENNITÀ DI NOSTRO SIGNORE GESÙ CRISTO RE",
                  "santo_del_giorno": "Santa Cecilia, vergine e martire"}),
        "Cristo Re il 22 novembre -> Proprio di santa Cecilia escluso")
    check(not LiturgiaRepository.proprio_applies(
        {"santo": "Santi Gioacchino e Anna", "letture": []},
        {"grado": "Domenica", "celebrazione": "XVII DOMENICA DEL TEMPO ORDINARIO"}),
        "domenica -> nessun Proprio")
    check(LiturgiaRepository.proprio_applies(
        {"santo": "Santi Cornelio, papa e Cipriano, vescovo, martiri"},
        {"grado": "Memoria", "celebrazione": "SANTI CORNELIO, PAPA, E CIPRIANO, VESCOVO, MARTIRI"}),
        "nomi composti riconosciuti")
    check(LiturgiaRepository.proprio_applies(
        {"santo": "Maria SS. Madre di Dio"},
        {"grado": "Solennità", "celebrazione": "MARIA SANTISSIMA MADRE DI DIO – SOLENNITÀ"}),
        "solennità con nome abbreviato")

    # Festa: solo il Proprio; Memoria: Biennale + Proprio; Feria: solo Biennale
    repo = LiturgiaRepository(Path("nessuna"), Path("nessuna"))
    letture = [{"titolo": "Seconda Lettura", "riferimento": "1", "fonte": "Dai «Discorsi»",
                "testo": "Testo del santo", "responsorio": ""}]
    proprio = {"santo": "Sant'Andrea, apostolo", "letture": letture}
    repo._find_biennale = lambda metadata: {  # noqa: E731 - stub del Biennale
        "tempo_liturgico": "Avvento", "settimana_del_tempo": "I",
        "giorno_settimana": "Lunedì", "letture": [
            {"titolo": "Prima Lettura", "riferimento": "1", "fonte": "Dal libro",
             "testo": "Testo feriale", "responsorio": ""}]}
    def labels(metadata, entry):
        return [s.label for s in repo._giorno_sections([], entry, metadata)]
    festa = labels({"grado": "Festa", "celebrazione": "SANT'ANDREA APOSTOLO - FESTA"}, proprio)
    check("Dal Proprio" in festa and "Dal Biennale" not in festa,
          "festa -> solo il Proprio, niente Biennale")
    memoria = labels({"grado": "Memoria", "celebrazione": "SANT'ANDREA APOSTOLO - MEMORIA"}, proprio)
    check("Dal Biennale" in memoria and "Dal Proprio" in memoria
          and memoria.index("Dal Biennale") < memoria.index("Dal Proprio"),
          "memoria -> Biennale poi Proprio")
    feria = labels({"grado": "Feria", "celebrazione": "LUNEDÌ DELLA I SETTIMANA DI AVVENTO"}, proprio)
    check("Dal Biennale" in feria and "Dal Proprio" not in feria,
          "feria -> solo il Biennale")


def main() -> int:
    for test in (test_calendario, test_cleaner, test_webapp, test_omelia,
                 test_amministrazione, test_biennale_data, test_proprio_festa):
        test()
    print(f"\nTutti i test superati ({PASSED} controlli).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
