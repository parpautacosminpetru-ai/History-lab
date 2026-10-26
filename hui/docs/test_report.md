# Raport al verificărilor executate

Data: 26 octombrie 2026. Codul verificat în CI: `aa2ef9af786cc78cd7708fb589bf62e3c13d0f19`. Ultima actualizare a raportului nu modifică acel cod.

## Local — Linux

- `python -m pytest hui/indexer/tests -q`: **49 trecute**, inclusiv OCR Tesseract real în engleză și respingerea coliziunilor de căi pe Windows.
- `npm test`: **27 trecute** pentru aplicația HistoryLab existentă.
- `python -m compileall -q hui/indexer/src hui/scripts`: executat fără erori.
- Export/import `.hui`: exercitat pe documente originale sintetice, cu și fără originale, corupere și recuperare.
- Coordonate: verificate față de pixeli reali la rotațiile 0°, 90°, 180°, 270° și pagini decupate.
- Unicode: diacritice și caracter suplimentar, cu offseturi în puncte de cod.
- Furnizori AI: numai adaptorul determinist și verificările de acord/configurare au fost executate; nu s-a trimis text unui model real sau unui API extern.

Benchmark local: 10.000 de segmente sintetice, 1.000 de potriviri, 30 de interogări, limită 50. Mediană **2,5874 ms**, p95 **3,0767 ms**. Baza: 3.833.856 octeți. Vezi `benchmark-result.json` pentru platformă și planul SQL. Măsurarea nu include OCR, randare, import de pachet sau interfață și nu promite aceiași timpi pe alte dispozitive.

SDK-ul Flutter local a fost oprit de controlul automat când procesul a încercat să acceseze adresa de metadate a instanței cloud. Comanda nu a fost reluată în acest mediu; verificările Flutter sunt efectuate prin GitHub Actions.

## GitHub Actions

| Verificare | Rezultat efectiv | Rulare |
| --- | --- | --- |
| Python Linux | **49 trecute**, inclusiv Tesseract real | [CI Python](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640070) |
| Python Windows | **48 trecute, 1 omis**: Tesseract nu este instalat în runner | [CI Python](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640070) |
| Aplicația existentă | **27 trecute**, pe ambele sisteme | [CI Python și HistoryLab](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640070) |
| Analiză Flutter și teste Linux | Analiză reușită, **10 teste trecute** | [CI Flutter](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640249) |
| Flutter Windows | **10 teste trecute**, build release reușit | [CI Windows](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640066) |
| APK Android | Build debug reușit; audit `aapt` fără `INTERNET` sau `ACCESS_NETWORK_STATE` | [CI Android](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640269) |
| Android pe emulator API 35, x86_64 | **1 test de integrare trecut**: import pachet real, aceleași rezultate SQL, pagină originală 2 în pdfrx | [CI Android offline](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640234) |

Testul de integrare a executat `adb shell svc wifi disable` și `adb shell svc data disable` înainte de aplicație. Harness-ul de test are o permisiune temporară de loopback pentru comunicarea Flutter; APK-ul distribuit este compilat separat și nu are permisiuni de rețea.

## Artefacte produse

| Artefact | Descărcare | SHA-256 al arhivei Actions |
| --- | --- | --- |
| HUI Reader Windows, întregul director release | [Windows](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640066/artifacts/12649207979) | `7afc866ce02c855f5e8ba166c4cf69b98417d5b41b18a35ce2c3d794787164db` |
| HUI Reader Android debug APK | [Android](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40321640269/artifacts/12648783944) | `546aa04801d2b556ca8bec8cebd086d3d3c5b112aaa628c8f6cb0ecc98b58acf` |

Artefactele Actions au retenție limitată; aceste două arhive au expirarea indicată de GitHub la 24 ianuarie 2027. Se pot recompila din codul verificat folosind instrucțiunile din repository.

Nu s-au executat teste pe un telefon fizic sau o verificare interactivă a atelierului Tk pe Windows. Testarea semantică folosește exemple controlate, nu un corpus istoric validat exhaustiv.
