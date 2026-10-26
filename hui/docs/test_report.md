# Raport al verificărilor executate

Data: 26 octombrie 2026. Rezultatele de mai jos disting codul testat de verificările încă în desfășurare.

## Local — Linux

- `python -m pytest hui/indexer/tests -q`: **41 trecute**, inclusiv OCR Tesseract real în engleză.
- `npm test`: **27 trecute** pentru aplicația HistoryLab existentă.
- `python -m compileall -q hui/indexer/src hui/scripts`: executat fără erori.
- Export/import `.hui`: exercitat pe documente originale sintetice, cu și fără originale, corupere și recuperare.
- Coordonate: verificate față de pixeli reali la rotațiile 0°, 90°, 180°, 270° și pagini decupate.
- Unicode: diacritice și caracter suplimentar, cu offseturi în puncte de cod.
- Furnizori AI: numai adaptorul determinist și verificările de acord/configurare au fost executate; nu s-a trimis text unui model real sau unui API extern.

Benchmark local: 10.000 de segmente sintetice, 1.000 de potriviri, 30 de interogări, limită 50. Mediană **2,5874 ms**, p95 **3,0767 ms**. Baza: 3.833.856 octeți. Vezi `benchmark-result.json` pentru platformă și planul SQL. Măsurarea nu include OCR, randare, import de pachet sau interfață și nu promite aceiași timpi pe alte dispozitive.

SDK-ul Flutter local a fost oprit de controlul automat când procesul a încercat să acceseze adresa de metadate a instanței cloud. Comanda nu a fost reluată în acest mediu; verificările Flutter sunt efectuate prin GitHub Actions.

## GitHub Actions

- Python și testele existente: executate cu succes pe Windows și Linux pe branch-ul PR.
- Analiza Flutter: executată cu succes în CI după eliminarea testului de contor generat de `flutter create` și a unui import neutilizat.
- Android: [build reușit și audit al permisiunilor](https://github.com/parpautacosminpetru-ai/History-lab/actions/runs/40318455998). APK debug generat; `aapt` confirmă absența `INTERNET` și `ACCESS_NETWORK_STATE`.
- Testele Flutter de navigare, build-ul Windows și integrarea Android sunt în verificare; rezultatele finale se vor consemna înainte de încheierea PR-ului.

Nu s-au executat teste pe un telefon fizic sau o verificare interactivă a atelierului Tk pe Windows. Testarea semantică folosește exemple controlate, nu un corpus istoric validat exhaustiv.
