# Conversione dei testi grezzi del Biennale

File grezzi esaminati: 797

| Destinazione | File prodotti |
|---|---|
| biennale/ (ciclo stagionale, schema di data/biennale) | 652 |
| biennale/ con codice per data (17-24 dic, 29-31 dic, 2-12 gen; campo `data`) | 42 |
| proprio/ (santi e feste a data fissa, schema di data/proprio) | 88 |
| da_assegnare/ (feste mobili e file di prova) | 5 |
| duplicati/ (stessa data in Santi/ e Feste/) | 6 |
| saltati (duplicati esatti o già coperti) | 5 |

Letture totali estratte: 1651

## Regole di mappatura

- `bien_dispari` / `dispari` → ciclo **I**; `bien_pari` / `pari` → ciclo **II**.
- `Ordinario/NN_BIEN` → Tempo Ordinario, settimana NN in numeri romani; `1DOM`…`7SAB` → giorno.
- `Quaresima/QUA0N` → Quaresima N; `QUA06` giovedì/venerdì/sabato → **Triduo Pasquale** (settimana vuota).
- `Ceneri/` → Quaresima, settimana **0** (come nei metadati CEI).
- `Pasqua/PAS0N` → Tempo di Pasqua N; `8DOM` → domenica della settimana successiva (Pentecoste = VIII).
- `Avvento/AVV0N` → Avvento N; `Avvento/1724dic` e `Natale/` → voci a **data fissa** (cartella biennale_data/).
- `Santi/` e `Feste/` con nome `MMGG` → Proprio (`GG-MM.json`); nomi non numerici → da_assegnare/.
- Il tag `(D)`, `(P)`, `(I)`, `(II)`, `(I/II)` nei titoli è tolto nelle voci stagionali (il ciclo è dato dalla cartella).
- Le letture alternative (`Oppure:`, `Una delle seguenti:`) sono voci separate con suffisso **(oppure)** nel titolo.
- `riferimento` = contenuto tra parentesi della riga della fonte (es. `14,1-24`, `Lib. 1,2.5.7-9`).
- `<` e `>` dell'OCR sono resi come « e »; i paragrafi sono separati da `\n`.
- L'`Orazione` finale, quando presente, è conservata nel campo `orazione`.
- Ogni JSON riporta in `fonte_raw` il file grezzo di origine.

## Giornate assenti nella sorgente (ciclo stagionale)

Mancano 56 combinazioni tempo/settimana/giorno/ciclo:

- Tempo Ordinario VIII Sabato — ciclo I
- Tempo Ordinario XII Sabato — ciclo I
- Tempo Ordinario XVII Lunedì — ciclo I
- Tempo Ordinario XVII Giovedì — ciclo I
- Tempo Ordinario XXIX Venerdì — ciclo I
- Tempo Ordinario XXXI Domenica — ciclo I
- Tempo Ordinario XXXIV Domenica — ciclo I
- Quaresima IV Sabato — ciclo I
- Tempo di Pasqua I Domenica — ciclo I
- Tempo di Pasqua I Lunedì — ciclo I
- Tempo di Pasqua I Giovedì — ciclo I
- Tempo di Pasqua I Venerdì — ciclo I
- Tempo di Pasqua II Giovedì — ciclo I
- Tempo di Pasqua III Venerdì — ciclo I
- Tempo di Pasqua IV Domenica — ciclo I
- Tempo di Pasqua IV Martedì — ciclo I
- Tempo di Pasqua IV Mercoledì — ciclo I
- Tempo di Pasqua IV Giovedì — ciclo I
- Tempo di Pasqua IV Venerdì — ciclo I
- Tempo di Pasqua IV Sabato — ciclo I
- Tempo di Pasqua VI Domenica — ciclo I
- Tempo di Pasqua VI Mercoledì — ciclo I
- Tempo di Pasqua VI Giovedì — ciclo I
- Tempo di Pasqua VI Venerdì — ciclo I
- Tempo di Pasqua VI Sabato — ciclo I
- Avvento III Sabato — ciclo I
- Tempo Ordinario II Venerdì — ciclo II
- Tempo Ordinario III Lunedì — ciclo II
- Tempo Ordinario VIII Giovedì — ciclo II
- Tempo Ordinario X Mercoledì — ciclo II
- Tempo Ordinario XII Lunedì — ciclo II
- Tempo Ordinario XVIII Venerdì — ciclo II
- Tempo Ordinario XX Mercoledì — ciclo II
- Tempo Ordinario XXIX Domenica — ciclo II
- Quaresima I Giovedì — ciclo II
- Quaresima III Martedì — ciclo II
- Tempo di Pasqua IV Domenica — ciclo II
- Tempo di Pasqua IV Lunedì — ciclo II
- Tempo di Pasqua IV Martedì — ciclo II
- Tempo di Pasqua IV Mercoledì — ciclo II
- Tempo di Pasqua IV Giovedì — ciclo II
- Tempo di Pasqua IV Venerdì — ciclo II
- Tempo di Pasqua IV Sabato — ciclo II
- Tempo di Pasqua V Mercoledì — ciclo II
- Tempo di Pasqua VI Domenica — ciclo II
- Tempo di Pasqua VI Martedì — ciclo II
- Tempo di Pasqua VI Mercoledì — ciclo II
- Tempo di Pasqua VI Giovedì — ciclo II
- Tempo di Pasqua VI Venerdì — ciclo II
- Tempo di Pasqua VI Sabato — ciclo II
- Tempo di Pasqua VII Domenica — ciclo II
- Tempo di Pasqua VII Martedì — ciclo II
- Tempo di Pasqua VII Mercoledì — ciclo II
- Tempo di Pasqua VII Giovedì — ciclo II
- Tempo di Pasqua VII Venerdì — ciclo II
- Tempo di Pasqua VII Sabato — ciclo II

## File saltati

- `Pasqua/PAS02/bien_pari/7.sab.txt` — duplicato di 7SAB.txt
- `Santi/0102.txt` — ferie 2-5 gennaio: già in Natale/ (entrambi i cicli)
- `Santi/0103.txt` — ferie 2-5 gennaio: già in Natale/ (entrambi i cicli)
- `Santi/0104.txt` — ferie 2-5 gennaio: già in Natale/ (entrambi i cicli)
- `Santi/0105.txt` — ferie 2-5 gennaio: già in Natale/ (entrambi i cicli)

## Avvisi per file (211 file)

### Avvento/1724dic/dispari/17_dicembre.txt
- Seconda Lettura: sottotitolo separato euristicamente «Dio Padre lo ha fatto essere per noi misericordia »

### Avvento/1724dic/dispari/22_dicembre.txt
- Prima Lettura: sottotitolo separato euristicamente «Liberazione di Israele»

### Avvento/1724dic/dispari/23_dicembre.txt
- Seconda Lettura: sottotitolo separato euristicamente «Colui che è nato una volta da Maria nasce in noi o»

### Avvento/1724dic/pari/20_dicembre.txt
- Prima Lettura: sottotitolo separato euristicamente «Dio è il solo Signore del tempo futuro»

### Avvento/AVV01/bien_dispari/7SAB.txt
- Seconda Lettura: responsorio assente (sorgente troncata?)

### Avvento/AVV02/bien_pari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Nel giorno del giudizio il regno di Dio si afferme»

### Avvento/AVV03/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Salita dei Gentili al monte del Signore»

### Avvento/AVV03/bien_pari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Ci sarà un regno di giustizia»

### Avvento/AVV03/bien_pari/5GIO.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla Costituzione dogmatica “Dei Verbum»)

### Feste/0101.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalle “Lettere” di sant’Agostino, vescov»)
- Vangelo: sottotitolo incollato al testo (fonte «Dal vangelo secondo Luca»)
- Terza Lettura: sottotitolo incollato al testo (fonte «Dalle “Omelie” si san Cirillo d’Alessand»)
- Terza Lettura: sottotitolo separato euristicamente «Con grande timore e reverenza dobbiamo contemplare»

### Feste/0106.txt
- Terza Lettura: sottotitolo separato euristicamente «Accogliamo anche noi nel nostro cuore quella grand»
- Terza Lettura: sottotitolo incollato al testo (fonte «Dai “Discorsi” di sant’Odilone di Cluny,»)

### Feste/0222.txt
- Terza Lettura: sottotitolo separato euristicamente «Poiché aveva mostrato con la confessione una fede »
- Terza Lettura: sottotitolo separato euristicamente «La fermezza che Cristo dona a Pietro, Pietro la co»
- Terza Lettura: sottotitolo incollato al testo (fonte «Dai “Trattati su Giovanni” di sant’Agost»)

### Feste/0503.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal trattato “Sulla prescrizione degli e»)
- Terza Lettura: sottotitolo separato euristicamente «L’unica nostra preoccupazione deve essere Dio»

### Feste/0514.txt
- Seconda Lettura: sottotitolo separato euristicamente «Mostraci, Signore, chi hai designato»
- Vangelo: sottotitolo incollato al testo (fonte «Dal vangelo secondo Giovanni»)
- Terza Lettura: sottotitolo separato euristicamente «Il Signore ha fatto ciò che ha insegnato, gli apos»

### Feste/0725.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalle “Omelie sul vangelo di Matteo” di »)

### Feste/0815.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla costituzione apostolica “Munificen»)
- Seconda Lettura: sottotitolo separato euristicamente «Maria non si è allontanata dal mondo»
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dall’“Omelia sulla dormizione della Madr»)
- Seconda Lettura: sottotitolo separato euristicamente «Maria adempì la disposizione fissata dalla Provvid»
- Terza Lettura: sottotitolo incollato al testo (fonte «Dai “Discorsi” di san Pascasio Radberto,»)

### Feste/0921.txt
- Seconda Lettura: sottotitolo separato euristicamente «Gli araldi degli oracoli evangelici annunziano al »
- Vangelo: sottotitolo incollato al testo (fonte «Dal vangelo secondo Matteo»)
- Terza Lettura: sottotitolo incollato al testo (fonte «Dalle “Omelie” di san Beda il Venerabile»)

### Feste/1004.txt
- Prima Lettura: sottotitolo separato euristicamente «A ciascuno è stata data la sua grazia, per edifica»
- Seconda Lettura: sottotitolo separato euristicamente «Dobbiamo essere semplici, umili e puri»
- Vangelo: sottotitolo incollato al testo (fonte «Dal vangelo secondo Matteo»)
- Terza Lettura: sottotitolo separato euristicamente «La saggezza è presso gli umili»

### Feste/1130.txt
- Seconda Lettura: sottotitolo separato euristicamente «Dio ha affidato a noi il ministero della riconcili»
- Terza Lettura: sottotitolo incollato al testo (fonte «Dalle “Omelie sul vangelo di Giovanni” d»)

### Feste/1225.txt
- Prima Lettura: sottotitolo separato euristicamente «La radice di Iesse e la pace messianica»
- Prima Lettura: sottotitolo separato euristicamente «Annuncio della liberazione»
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro del profeta Isaia»)
- Seconda Lettura: sottotitolo separato euristicamente «Riconosci, cristiano, la tua dignità»
- Seconda Lettura: sottotitolo separato euristicamente «Il nome di Cristo è Pace»
- Seconda Lettura: sottotitolo separato euristicamente «Nella Natività di Cristo la divinità si umilia, l’»
- Seconda Lettura: sottotitolo separato euristicamente «La pace che ci viene dal Signore non avrà mai fine»
- Terza Lettura: sottotitolo separato euristicamente «Ecco la Vergine concepirà e partorirà un Figlio ch»
- Terza Lettura: sottotitolo separato euristicamente «Oggi ci è nato un Salvatore»
- Terza Lettura: sottotitolo incollato al testo (fonte «Dal “Discorso nel giorno della Natività »)
- Terza Lettura: sottotitolo incollato al testo (fonte «Dalle “Omelie” di san Basilio Magno, ves»)

### Feste/1226.txt
- Terza Lettura: sottotitolo separato euristicamente «Beati i perseguitati per causa mia»
- Vangelo: fonte assente

### Feste/2° domenica dopo Natale.txt
- Terza Lettura: sottotitolo separato euristicamente «Dio si è fatto uomo perché l’uomo diventasse Dio»
- Terza Lettura: sottotitolo separato euristicamente «Era venuto a salvare, ma fu anche necessario che m»

### Feste/santafamiglia.txt
- Prima Lettura: sottotitolo separato euristicamente «La vita cristiana nella famiglia»
- Seconda Lettura: sottotitolo separato euristicamente «Il bambino Gesù, che oggi è nato per noi, è la ver»
- Vangelo: sottotitolo incollato al testo (fonte «Dal vangelo secondo Matteo»)
- Terza Lettura: sottotitolo incollato al testo (fonte «Dall’“Omelia” per il giorno di Natale di»)
- Terza Lettura: sottotitolo incollato al testo (fonte «Dalle “Omelie su Luca” di Origene, sacer»)
- Terza Lettura: sottotitolo separato euristicamente «Gesù cresceva in sapienza, età e grazia»
- Terza Lettura: responsorio assente (sorgente troncata?)

### Feste/sscorpo.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalle “Omelie diverse” di san Cirillo di»)

### Feste/sstrinita.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dai “Poemi teologici” di san Gregorio Na»)

### Natale/bien_dispari/0501.txt
- Prima Lettura: sottotitolo separato euristicamente «Esortazione alla vigilanza. Conclusione della lett»

### Natale/bien_dispari/0701.txt
- Prima Lettura: sottotitolo separato euristicamente «Lo Spirito del Signore è sopra il suo Servo»

### Natale/bien_dispari/0901.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro del profeta Isaia»)

### Natale/bien_dispari/1001.txt
- Prima Lettura: sottotitolo separato euristicamente «Si implora la venuta del Signore»

### Natale/bien_dispari/1101.txt
- Prima Lettura: sottotitolo separato euristicamente «Nuovi cieli e nuova terra»

### Natale/bien_dispari/3012.txt
- Prima Lettura: sottotitolo separato euristicamente «Cristo, Capo della Chiesa, e Paolo suo servo»

### Natale/bien_pari/0201.txt
- Prima Lettura: sottotitolo separato euristicamente «Cristo desidera l’amore della Chiesa sua sposa»

### Natale/bien_pari/0301.txt
- Prima Lettura: sottotitolo separato euristicamente «La Sposa cerca e loda lo sposo»

### Natale/bien_pari/0401.txt
- Prima Lettura: sottotitolo separato euristicamente «Lode della Sposa»

### Natale/bien_pari/0501.txt
- Prima Lettura: sottotitolo separato euristicamente «Ultime parole della Sposa e lode all’amore»

### Natale/bien_pari/0801.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro del profeta Isaia»)

### Natale/bien_pari/0901.txt
- Prima Lettura: sottotitolo separato euristicamente «Gli stranieri e gli eunuchi sono ammessi nella cas»

### Natale/bien_pari/1001.txt
- Prima Lettura: sottotitolo separato euristicamente «Il Signore viene»

### Natale/bien_pari/1101.txt
- Prima Lettura: sottotitolo separato euristicamente «Sion consola e incoraggia i suoi figli Coraggio, p»

### Natale/bien_pari/3012.txt
- Prima Lettura: sottotitolo separato euristicamente «Colloquio dello Sposo e della Sposa cioè di Cristo»

### Natale/bien_pari/3112.txt
- Prima Lettura: sottotitolo separato euristicamente «La Sposa cerca lo Sposo di cui ha udito la voce»

### Ordinario/01_BIEN/bien_pari/7SAB.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dai “Discorsi sull’Antico Testamento” di»)

### Ordinario/02_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «La giustificazione dell’uomo per mezzo di Gesù Cri»

### Ordinario/02_BIEN/bien_dispari/7SAB.txt
- Prima Lettura: sottotitolo separato euristicamente «Io sono di carne, venduto come schiavo del peccato»

### Ordinario/02_BIEN/bien_pari/7SAB.txt
- Prima Lettura: sottotitolo separato euristicamente «La circoncisione come segno di alleanza tra Dio e »

### Ordinario/03_BIEN/bien_dispari/7SAB.txt
- Seconda Lettura: sottotitolo separato euristicamente «Andate, istruite tutte le genti»

### Ordinario/04_BIEN/bien_pari/3MAR.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro della Genesi»)

### Ordinario/06_BIEN/bien_pari/7SAB.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla costituzione pastorale “Gaudium et»)

### Ordinario/06_BIEN/bien_pari/8DOM.txt
- Prima Lettura: sottotitolo separato euristicamente «Quelli che sono guidati dallo Spirito di Dio, cost»
- Seconda Lettura: sottotitolo separato euristicamente «Dio ha mandato nei nostri cuori lo Spirito del suo»
- Seconda Lettura: sottotitolo separato euristicamente «La Chiesa di Cristo è là dove viene predicata l’in»
- Pentecoste (ciclo pari) archiviata in Ordinario/06_BIEN/8DOM

### Ordinario/07_BIEN/bien_pari/3MAR.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal “Commento sui salmi” di sant’Agostin»)

### Ordinario/09_BIEN/bien_pari/5GIO.txt
- Seconda Lettura: sottotitolo separato euristicamente «Cristo sia formato in voi»

### Ordinario/10_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Giosuè, chiamato da Dio, esorta il popolo all’unit»

### Ordinario/10_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Per fede Raab ospita gli esploratori israeliti e l»
- Seconda Lettura: sottotitolo separato euristicamente «Non apparteniamo a noi stessi, ma a colui che ci h»

### Ordinario/10_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Il popolo attraversa il Giordano e celebra la Pasq»

### Ordinario/10_BIEN/bien_pari/5GIO.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla “Lettera ai Filippesi” di san Poli»)

### Ordinario/10_BIEN/bien_pari/6VEN.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla “Lettera ai cristiani di Magnesia”»)

### Ordinario/10_BIEN/bien_pari/7SAB.txt
- Seconda Lettura: sottotitolo separato euristicamente «Una sola preghiera, una sola speranza nella carità»

### Ordinario/11_BIEN/bien_dispari/2LUN.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal trattato “Sul Padre nostro” di san C»)

### Ordinario/11_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Cantico di Debora»

### Ordinario/11_BIEN/bien_dispari/6VEN.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal trattato “Sul Padre nostro” di san C»)

### Ordinario/11_BIEN/bien_pari/1DOM.txt
- Seconda Lettura: sottotitolo separato euristicamente «Avete Cristo in voi»

### Ordinario/11_BIEN/bien_pari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Liberazione del popolo e ritorno dei prigionieri. »

### Ordinario/11_BIEN/bien_pari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Nel tempio ricostruito il Signore manifesterà la s»

### Ordinario/11_BIEN/bien_pari/5GIO.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro del profeta Aggeo»)
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal trattato “Contro Fabiano” di san Ful»)

### Ordinario/11_BIEN/bien_pari/6VEN.txt
- Seconda Lettura: sottotitolo separato euristicamente «Luce perenne nel tempio del pontefice eterno Quant»

### Ordinario/12_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Dopo il cibo si chieda il perdono del peccato»

### Ordinario/12_BIEN/bien_pari/1DOM.txt
- Prima Lettura: sottotitolo separato euristicamente «Promessa al principe Zorobabele e a Giosuè sommo s»
- Seconda Lettura: sottotitolo separato euristicamente «Luce che illumina ogni uomo»

### Ordinario/12_BIEN/bien_pari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Costruzione del Tempio e celebrazione della Pasqua»

### Ordinario/12_BIEN/bien_pari/7SAB.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro di Neemia»)
- Seconda Lettura: sottotitolo separato euristicamente «La Gerusalemme celeste, madre dei primogeniti»

### Ordinario/13_BIEN/bien_dispari/1DOM.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal trattato “Sul Padre nostro” di san C»)

### Ordinario/13_BIEN/bien_dispari/5GIO.txt
- Seconda Lettura: sottotitolo separato euristicamente «Il peso del governo»

### Ordinario/13_BIEN/bien_pari/4MER.txt
- Seconda Lettura: sottotitolo separato euristicamente «Cristo ci donò la pace e ci ordinò di essere un so»

### Ordinario/13_BIEN/bien_pari/6VEN.txt
- Seconda Lettura: sottotitolo separato euristicamente «Egli stesso fondò la sua Chiesa»

### Ordinario/14_BIEN/bien_pari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Elogio della Sapienza creatrice»

### Ordinario/14_BIEN/bien_pari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «La sapienza e la stoltezza»

### Ordinario/14_BIEN/bien_pari/6VEN.txt
- Prima Lettura: sottotitolo separato euristicamente «L’uomo posto davanti a Dio»

### Ordinario/14_BIEN/bien_pari/7SAB.txt
- Prima Lettura: sottotitolo separato euristicamente «Elogio della donna forte»

### Ordinario/15_BIEN/bien_dispari/1DOM.txt
- Prima Lettura: sottotitolo separato euristicamente «Morte di Saul»
- Seconda Lettura: sottotitolo separato euristicamente «Egli è il nostro Dio e noi il popolo del suo pasco»

### Ordinario/15_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Davide, re di tutto Israele, conquista Gerusalemme»

### Ordinario/15_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «L’arca dell’alleanza viene trasportata in Gerusale»

### Ordinario/15_BIEN/bien_pari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Giobbe, tutto ricoperto di piaghe, è visitato dagl»

### Ordinario/15_BIEN/bien_pari/7SAB.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro di Giobbe»)

### Ordinario/16_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Il censimento del popolo e l’erezione dell’altare»

### Ordinario/16_BIEN/bien_pari/1DOM.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro di Giobbe»)

### Ordinario/16_BIEN/bien_pari/2LUN.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro di Giobbe»)

### Ordinario/16_BIEN/bien_pari/4MER.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro di Giobbe»)

### Ordinario/16_BIEN/bien_pari/7SAB.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro di Giobbe»)

### Ordinario/17_BIEN/bien_pari/7SAB.txt
- Seconda Lettura: sottotitolo separato euristicamente «La via per giungere alla vera vita»

### Ordinario/18_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal primo libro dei Re»)

### Ordinario/18_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Il grande aiuto offerto da Dio a Giòsafat, il re f»

### Ordinario/18_BIEN/bien_pari/7SAB.txt
- Seconda Lettura: sottotitolo separato euristicamente «Io sono l’alfa e l’omega, il primo e l’ultimo»

### Ordinario/19_BIEN/bien_pari/2LUN.txt
- Seconda Lettura: sottotitolo separato euristicamente «Il Signore è pronto alla misericordia e salva chi »

### Ordinario/19_BIEN/bien_pari/5GIO.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal “Commento sul Cantico dei Cantici” d»)

### Ordinario/20_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «La preghiera di Paolo perché i fedeli siano illumi»
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal trattato “L’ideale perfetto del cris»)

### Ordinario/20_BIEN/bien_dispari/5GIO.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalle “Omelie sul Cantico dei Cantici” d»)

### Ordinario/20_BIEN/bien_dispari/6VEN.txt
- Prima Lettura: sottotitolo separato euristicamente «Preghiera di Paolo perché i fedeli conoscano l’amo»

### Ordinario/20_BIEN/bien_pari/7SAB.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla “Spiegazione sull’Ecclesiaste” di »)

### Ordinario/22_BIEN/bien_dispari/1DOM.txt
- Prima Lettura: sottotitolo separato euristicamente «I regni di Amazia in Giuda e di Geroboamo II in Is»

### Ordinario/22_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Il giudizio di Dio su Giuda e Israele»

### Ordinario/22_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «La visita del Signore in Samaria e Betel»

### Ordinario/22_BIEN/bien_dispari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «Contro le donne di Samaria e il culto d’Israele»

### Ordinario/22_BIEN/bien_dispari/6VEN.txt
- Prima Lettura: sottotitolo separato euristicamente «Lamentazioni e ammonimenti»

### Ordinario/22_BIEN/bien_dispari/7SAB.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro del profeta Amos»)

### Ordinario/22_BIEN/bien_pari/6VEN.txt
- Seconda Lettura: sottotitolo separato euristicamente «La croce è per noi salvezza e vita eterna»

### Ordinario/23_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Il profeta è come un segno dell’amore di Dio per i»

### Ordinario/23_BIEN/bien_dispari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «Israele, castigato per la sua infedeltà, ritornerà»

### Ordinario/23_BIEN/bien_dispari/6VEN.txt
- Prima Lettura: sottotitolo separato euristicamente «La corruzione generale d’Israele anche fra i sacer»

### Ordinario/23_BIEN/bien_dispari/7SAB.txt
- Prima Lettura: sottotitolo separato euristicamente «La conversione non sincera è vana»

### Ordinario/24_BIEN/bien_dispari/1DOM.txt
- Prima Lettura: sottotitolo separato euristicamente «Contro i re, l’idolatria, le alleanze e il culto D»

### Ordinario/24_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Predizione dell’esilio e della sterilità»

### Ordinario/24_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «La misericordia di Dio non viene meno»

### Ordinario/24_BIEN/bien_dispari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «Ultima sentenza di riprovazione»

### Ordinario/24_BIEN/bien_dispari/6VEN.txt
- Prima Lettura: sottotitolo separato euristicamente «Invito alla conversione. Promessa della salvezza»

### Ordinario/25_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Rimproveri contro Gerusalemme»

### Ordinario/25_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Maledizioni agli operatori d’iniquità»

### Ordinario/25_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Il segno dell’Emmanuele nell’imminenza della guerr»

### Ordinario/25_BIEN/bien_dispari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «L’ira di Dio contro il regno d’Israele»

### Ordinario/25_BIEN/bien_dispari/6VEN.txt
- Prima Lettura: sottotitolo separato euristicamente «Vaticini contro la Samaria e i capi di Giuda»

### Ordinario/25_BIEN/bien_pari/3MAR.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dall’opuscolo “Sulla contemplazione dell»)

### Ordinario/25_BIEN/bien_pari/5GIO.txt
- Seconda Lettura: sottotitolo separato euristicamente «Che soave compagno è il profeta Davide in ogni cir»

### Ordinario/26_BIEN/bien_dispari/1DOM.txt
- Prima Lettura: sottotitolo separato euristicamente «Per le colpe dei suoi capi Gerusalemme sarà distru»

### Ordinario/26_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Il Signore giudica il suo popolo»

### Ordinario/26_BIEN/bien_dispari/3MAR.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dall’opuscolo “Sulla contemplazione dell»)

### Ordinario/26_BIEN/bien_dispari/6VEN.txt
- Prima Lettura: sottotitolo separato euristicamente «Annunzio della deportazione degli egiziani e degli»
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro di Giuditta»)
- Prima Lettura: tag (II) incoerente con la cartella (ciclo I)

### Ordinario/26_BIEN/bien_dispari/7SAB.txt
- Prima Lettura: sottotitolo separato euristicamente «Guarigione di Ezechia e profezia dell’esilio in Ba»

### Ordinario/27_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Inutilità delle alleanze fatte con altri popoli»

### Ordinario/27_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Minacce degli ambasciatori del re degli Assiri con»

### Ordinario/27_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal secondo libro dei Re»)

### Ordinario/27_BIEN/bien_dispari/6VEN.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal secondo libro dei Re»)

### Ordinario/27_BIEN/bien_dispari/7SAB.txt
- Prima Lettura: sottotitolo separato euristicamente «Il giudizio di Dio»
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla costituzione pastorale “Gaudium et»)

### Ordinario/28_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Infedeltà del popolo di Dio»

### Ordinario/28_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Invito alla conversione»

### Ordinario/28_BIEN/bien_dispari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «Si annunzia l’arrivo del devastatore»

### Ordinario/29_BIEN/bien_dispari/1DOM.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal secondo libro dei Re»)

### Ordinario/29_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal secondo libro delle Cronache»)

### Ordinario/29_BIEN/bien_dispari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «Maledizioni contro gli oppressori»

### Ordinario/30_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro del profeta Geremia»)

### Ordinario/30_BIEN/bien_dispari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «I popoli dovranno portare il giogo del re di Babil»

### Ordinario/30_BIEN/bien_dispari/7SAB.txt
- Prima Lettura: sottotitolo separato euristicamente «Lettera di Geremia agli Israeliti deportati a Babi»

### Ordinario/31_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Geremia, in carcere, esorta il re Sedecia alla pac»

### Ordinario/31_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro del profeta Geremia»)

### Ordinario/31_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Promesse della restaurazione d’Israele»

### Ordinario/31_BIEN/bien_dispari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «Annunzio della salvezza e di una nuova Alleanza»

### Ordinario/31_BIEN/bien_dispari/6VEN.txt
- Prima Lettura: sottotitolo separato euristicamente «Sorte di Geremia e del popolo dopo la conquista de»

### Ordinario/32_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Un’azione simbolica raffigura la distruzione di Ge»

### Ordinario/32_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «La gloria del Signore abbandona la città scellerat»

### Ordinario/32_BIEN/bien_dispari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «La deportazione del popolo adombrata in un’azione »

### Ordinario/32_BIEN/bien_pari/1DOM.txt
- Seconda Lettura: sottotitolo separato euristicamente «Promuovere la pace»

### Ordinario/32_BIEN/bien_pari/2LUN.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla costituzione pastorale “Gaudium et»)

### Ordinario/32_BIEN/bien_pari/6VEN.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla costituzione pastorale “Gaudium et»)

### Ordinario/33_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Vaticinio della rovina e della restaurazione»

### Ordinario/33_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «Ciascuno sarà giudicato in base alle proprie azion»

### Ordinario/34_BIEN/bien_dispari/2LUN.txt
- Prima Lettura: sottotitolo separato euristicamente «Futuro rinnovamento del popolo di Dio: il cuore nu»

### Ordinario/34_BIEN/bien_dispari/3MAR.txt
- Prima Lettura: sottotitolo separato euristicamente «La risurrezione del popolo di Dio, visione delle o»

### Ordinario/34_BIEN/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Un “segno” che adombra l’unificazione di Giuda e I»

### Ordinario/34_BIEN/bien_pari/1DOM.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dal libro dell’Apocalisse di san Giovann»)
- Seconda Lettura: sottotitolo separato euristicamente «Cristo ha umiliato se stesso entrando così per pri»

### Pasqua/PAS01/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «I cristiani vivono nel mondo come stranieri e pell»

### Pasqua/PAS01/bien_pari/1DOM.txt
- Seconda Lettura: sottotitolo separato euristicamente «Vi aspergerò con acqua pura e vi darò un cuore nuo»
- Terza Lettura: sottotitolo separato euristicamente «Cristo risuscitato dai morti non muore più»
- Quarta Lettura: sottotitolo incollato al testo (fonte «Dal vangelo secondo Matteo»)
- Quarta Lettura: responsorio assente (sorgente troncata?)

### Pasqua/PAS01/bien_pari/2LUN.txt
- Vangelo: sottotitolo incollato al testo (fonte «Dal vangelo secondo Matteo»)
- Terza Lettura: sottotitolo separato euristicamente «Ecco, apparirò all’esterno per ricondurti in te st»

### Pasqua/PAS01/bien_pari/3MAR.txt
- Seconda Lettura: sottotitolo separato euristicamente «Giustamente in questi giorni siamo traboccanti di »

### Pasqua/PAS01/bien_pari/5GIO.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal “Trattato sulla Solennità della Pasq»)

### Pasqua/PAS02/bien_dispari/4MER.txt
- Prima Lettura: sottotitolo separato euristicamente «Messaggio alle Chiese di Pergamo e Tiatira»

### Pasqua/PAS02/bien_dispari/7SAB.txt
- Seconda Lettura: sottotitolo separato euristicamente «L’opera della salvezza Dio»

### Pasqua/PAS02/bien_pari/5GIO.txt
- Prima Lettura: sottotitolo separato euristicamente «Inizio del discorso di Stefano sulla storia dei Pa»
- Seconda Lettura: sottotitolo separato euristicamente «I Misteri antichi e nuovi»

### Pasqua/PAS02/bien_pari/7SAB.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dagli Atti degli Apostoli»)

### Pasqua/PAS03/bien_dispari/2LUN.txt
- Seconda Lettura: sottotitolo separato euristicamente «Stirpe eletta, sacerdozio regale»

### Pasqua/PAS03/bien_dispari/3MAR.txt
- Seconda Lettura: sottotitolo separato euristicamente «Siamo giustificati per mezzo della grazia»

### Pasqua/PAS03/bien_dispari/4MER.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla “Prima Apologia a favore dei crist»)

### Pasqua/PAS03/bien_pari/7SAB.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal trattato “Sull’ ideale del perfetto »)

### Pasqua/PAS04/bien_dispari/2LUN.txt
- Seconda Lettura: sottotitolo separato euristicamente «Lo Spirito dà la vita»

### Pasqua/PAS05/bien_dispari/5GIO.txt
- Seconda Lettura: sottotitolo separato euristicamente «Siamo figli di Dio e costituiamo in Cristo una sol»

### Pasqua/PAS05/bien_pari/7SAB.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dalla “Prima Apologia a favore dei crist»)

### Pasqua/PAS06/bien_dispari/2LUN.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dai “Trattati sulla prima lettera di Gio»)

### Pasqua/PAS06/bien_dispari/3MAR.txt
- Seconda Lettura: sottotitolo separato euristicamente «Chi fa la volontà di Dio, rimane in eterno»

### Pasqua/PAS07/bien_dispari/1DOM.txt
- Prima Lettura: sottotitolo separato euristicamente «Ascendendo in cielo, Cristo ha distribuito doni ag»
- Seconda Lettura: sottotitolo separato euristicamente «Le ultime parole di Cristo prima di ascendere al c»

### Pasqua/PAS07/bien_dispari/2LUN.txt
- Seconda Lettura: sottotitolo separato euristicamente «Per mezzo dello Spirito Santo, l’anima è purificat»

### Pasqua/PAS07/bien_dispari/6VEN.txt
- nessuna lettura riconosciuta

### Pasqua/PAS07/bien_dispari/7SAB.txt
- Prima Lettura: sottotitolo incollato al testo (fonte «Dalla “Seconda Omelia sulla Pentecoste” »)

### Pasqua/PAS07/bien_dispari/8DOM.txt
- Prima Lettura: sottotitolo separato euristicamente «Quelli che sono guidati dallo Spirito di Dio, cost»
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal “Discorso sullo Spirito Santo” di sa»)

### Pasqua/PAS07/bien_pari/2LUN.txt
- Seconda Lettura: sottotitolo incollato al testo (fonte «Dal “Commento sul vangelo di Giovanni” d»)

### Quaresima/QUA01/bien_dispari/1DOM.txt
- Seconda Lettura: sottotitolo separato euristicamente «Chi è in grado di parlare della carità di Dio?»

### Quaresima/QUA01/bien_dispari/2LUN.txt
- Seconda Lettura: sottotitolo separato euristicamente «Io salverò il mio popolo»

### Quaresima/QUA01/bien_pari/3MAR.txt
- Seconda Lettura: tag (D) incoerente con la cartella (ciclo II)

### Quaresima/QUA02/bien_dispari/6VEN.txt
- Seconda Lettura: sottotitolo separato euristicamente «I prodigi di Dio»

### Quaresima/QUA04/bien_dispari/3MAR.txt
- Seconda Lettura: tag (P) incoerente con la cartella (ciclo I)

### Quaresima/QUA06/bien_dispari/7SAB.txt
- Terza Lettura: sottotitolo separato euristicamente «La morte di Cristo e dei cristiani»

### Quaresima/QUA06/bien_pari/6VEN.txt
- Terza Lettura: sottotitolo separato euristicamente «Il Cristo consegnò la sua anima nelle mani del Pad»
- Terza Lettura: responsorio assente (sorgente troncata?)

### Santi/0503.txt
- stessa data di Feste/0503.txt: conservata come duplicato

### Santi/0514.txt
- stessa data di Feste/0514.txt: conservata come duplicato

### Santi/0711.txt
- Prima Lettura: solo riferimento «Sir 45,1-6» (v. pag.)
- Prima Lettura: solo riferimento «Fil 3,7–4,1.4-9» (v. pag.)

### Santi/0715.txt
- Prima Lettura: solo riferimento «Tt 1,7-11; 2,1-8» (v. pag.)
- Prima Lettura: solo riferimento «Sir 39,1c-10» (v. pag.)

### Santi/0722.txt
- Prima Lettura: solo riferimento «Col 3,1-17» (v. pag.)
- Prima Lettura: solo riferimento «Rm 12,1-21» (v. pag.)

### Santi/0729.txt
- Prima Lettura: solo riferimento «Col 3,1-17» (v. pag.)
- Prima Lettura: solo riferimento «Rm 12,1-21» (v. pag.)

### Santi/0731.txt
- Prima Lettura: solo riferimento «1Pt 5,1-11» (v. pag.)
- Prima Lettura: solo riferimento «Col 3,1-17» (v. pag.)
- Prima Lettura: solo riferimento «Rm 12,1-21» (v. pag.)

### Santi/0801.txt
- Prima Lettura: solo riferimento «Tt 1,7-11; 2,1-8» (v. pag.)
- Prima Lettura: solo riferimento «Sir 39,1c-10» (v. pag.)

### Santi/0804.txt
- Prima Lettura: solo riferimento «1Pt 5,1-11» (v. pag.)

### Santi/0808.txt
- Prima Lettura: solo riferimento «Fil 3,7–4,1.4-9» (v. pag.)
- Prima Lettura: solo riferimento «1Pt 5,1-11» (v. pag.)

### Santi/0811.txt
- Prima Lettura: solo riferimento «1Cor 7,25-40» (v. pag.)
- Prima Lettura: solo riferimento «Fil 3,7–4,1.4-9» (v. pag.)

### Santi/0814.txt
- Prima Lettura: solo riferimento «1Cor 4,7–5,8» (v. pag.)
- Prima Lettura: solo riferimento «1Pt 5,1-11» (v. pag.)

### Santi/0820.txt
- Prima Lettura: solo riferimento «Sir 39,1c-10» (v. pag.)
- Prima Lettura: solo riferimento «Fil 3,7–4,1.4-9» (v. pag.)

### Santi/0821.txt
- Prima Lettura: solo riferimento «Tt 1,7-11; 2,1-8» (v. pag.)

### Santi/0827.txt
- Prima Lettura: solo riferimento «Col 3,1-17» (v. pag.)
- Prima Lettura: solo riferimento «Rm 12,1-21» (v. pag.)

### Santi/0828.txt
- Prima Lettura: solo riferimento «Tt 1,7-11; 2,1-8» (v. pag.)
- Prima Lettura: solo riferimento «Sir 39,1c-10» (v. pag.)

### Santi/0916.txt
- Prima Lettura: responsorio assente (sorgente troncata?)
- Seconda Lettura: responsorio assente (sorgente troncata?)

### Santi/0920.txt
- Prima Lettura: responsorio assente (sorgente troncata?)

### Santi/0921.txt
- stessa data di Feste/0921.txt: conservata come duplicato

### Santi/1004.txt
- stessa data di Feste/1004.txt: conservata come duplicato

### Santi/1007.txt
- Prima Lettura: fonte assente

### Santi/1125.txt
- Prima Lettura: responsorio assente (sorgente troncata?)

### Santi/1130.txt
- sostituisce Feste/1130.txt (meno letture), spostato in duplicati/

### Santi/1226.txt
- stessa data di Feste/1226.txt: conservata come duplicato
