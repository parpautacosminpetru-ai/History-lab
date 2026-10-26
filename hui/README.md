# Historical Universal Index — HUI 0.1

Prototip local pentru acces determinist la pasaje originale, cu proveniență verificabilă. Indexer construiește baza. Reader o consultă offline. Istoricul interpretează și scrie.

Aplicația HistoryLab din `../app/` este păstrată. HUI are altă aplicație, altă bază și alt format de transfer; nu șterge și nu convertește automat datele vechi.

## Flux funcțional

1. Importă PDF-uri în Indexer pe Windows sau Linux. Originalul este copiat nemodificat și identificat prin SHA-256.
2. PDFium extrage text și poziții de caractere; pentru scanări, Tesseract este apelat local numai cu o limbă indicată explicit.
3. Consultă structura propusă și textul nemodificat lângă imagine. Creează indici, selectează intervale și documentează relații.
4. Confirmă sau respinge propunerile. Negația, modalitatea, atribuirea și conectorii sunt stocate distinct.
5. Publică și exportă `.hui`. PDF-urile și imaginile se includ numai la confirmarea dreptului de distribuire.
6. Importă pachetul în Reader. Caută prin SQL/FTS5, deschide pagina originală, evidențiază pasajul și navighează între surse și apariții.

**Limita inițială de segmentare este pagina.** „Același segment” în interogările prototipului înseamnă același segment de pagină, nu automat aceeași propoziție. Relațiile nu sunt deduse din coapariție.

## Pornire rapidă — Indexer

Din rădăcina repository-ului, cu Python 3.12:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e "hui/indexer[test]"
python -m hui_indexer.cli --workspace hui-workspace gui
```

Din terminal, pentru un PDF digital:

```powershell
python -m hui_indexer.cli --workspace hui-workspace ingest "C:\Surse\carte.pdf" --title "Titlul exact" --author "Autorul" --language ro --edition "Ediția consultată"
python -m hui_indexer.cli --workspace hui-workspace search domnie
python -m hui_indexer.cli --workspace hui-workspace list segments
python -m hui_indexer.cli --workspace hui-workspace coverage
python -m hui_indexer.cli --workspace hui-workspace publish --description "Index revizuit"
python -m hui_indexer.cli --workspace hui-workspace export colectie.hui
```

Ultima comandă exportă numai indexul. Pentru a include scanările și PDF-urile, adaugă `--include-originals --rights-confirmed` numai dacă ai dreptul de distribuire. Deschiderea atelierului nu pornește un model AI.

Documente demonstrative originale, cu etichetare explicită și fără afirmații istorice:

```powershell
python -m hui_indexer.demo --output hui/build/demo
```

Pachetul rezultat este `hui/build/demo/demo.hui`. Baza Reader pornește goală; fixture-ul nu se importă automat.

## Compilare și pornire — Reader

Necesită Flutter **3.38.5** și uneltele platformei țintă. Din rădăcina repository-ului:

```powershell
python hui/scripts/prepare_reader.py
cd hui/app
flutter pub get
flutter analyze --no-fatal-infos
flutter test
flutter run -d windows
```

Scriptul generează configurațiile native standard Flutter pentru Windows și Android și elimină permisiunile de rețea din aplicația livrabilă. Codul aplicației este în `hui/app/lib`; dependențele sunt fixate prin `pubspec.lock`.

```powershell
flutter build windows --release
flutter build apk --debug
```

Build-urile se verifică și în Actions: **HUI Windows Reader**, **HUI Android APK**, **HUI Flutter analyze and tests**. APK-ul de test și întregul director Windows se descarcă din artefactele unei rulări reușite. Nu instala doar fișierul `.exe` fără DLL-urile și datele care îl însoțesc.

Artefacte compilate și verificate pentru prototipul 0.1: [Windows](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640066/artifacts/12649207979) și [APK Android debug](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640269/artifacts/12648783944). [Raportul](docs/test_report.md) identifică exact codul, testele și hash-urile arhivelor.

## Testare

```powershell
python -m pytest hui/indexer/tests -q
npm test
python hui/scripts/benchmark.py --segments 10000 --iterations 30
```

Vectorii din `app/test/fixtures/queries.json` compară aceleași interogări Python/Dart pe un pachet SQLite exportat real. Testele de navigare verifică sursă → pagină → indice → apariție. Integrarea Android are un workflow separat cu Wi-Fi și datele mobile dezactivate; acesta nu produce APK-ul distribuit.

## Documentație

| Subiect | Document |
| --- | --- |
| Arhitectură și delimitarea componentelor | [architecture.md](docs/architecture.md) |
| Model, coordonate și identificatori | [database.md](docs/database.md) |
| Import, adnotare, validare și publicare | [indexing_protocol.md](docs/indexing_protocol.md) |
| Reguli semantice și interogări | [semantic_rules.md](docs/semantic_rules.md) |
| Unicode și limbi | [multilingual.md](docs/multilingual.md) |
| Pachete, backup și recuperare | [offline.md](docs/offline.md) |
| Instalare Windows | [installation_windows.md](docs/installation_windows.md) |
| APK și utilizare Android | [installation_android.md](docs/installation_android.md) |
| Teste și criterii de acceptare | [validation.md](docs/validation.md) |
| Rezultate executate | [test_report.md](docs/test_report.md) |
| Limitări și continuare | [limitations.md](docs/limitations.md) |

Codul nou HUI este sub licență MIT. Fontul demonstrativ are licența proprie inclusă. Nu sunt incluse cărți comerciale, chei API sau telemetrie.
