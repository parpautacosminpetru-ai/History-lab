# Instalare Windows

## Indexer

1. Instalează Python 3.12 cu Tcl/Tk și acces în PATH. Folosește un mediu virtual în repository.
2. Rulează din rădăcină `python -m pip install -e "hui/indexer[test]"`. Extra-ul `test` adaugă generatorul documentelor demonstrative și testele; extragerea propriu-zisă cere numai dependențele de bază.
3. Pentru scanări, instalează separat Tesseract și limbile necesare. Verifică `tesseract --version` și `tesseract --list-langs`. Pentru română este necesar `ron.traineddata`, nu doar `eng`.
4. Pornește `python -m hui_indexer.cli --workspace hui-workspace gui`. Pentru import fără OCR, GUI funcționează cu PDF-uri digitale fără Tesseract.

Datele de lucru sunt în `hui-workspace`: `catalog.sqlite`, `originals/` și `pages/`. Fă backup/export înainte să muți sau să ștergi directorul. Nu publica documentele personale în repository.

În PowerShell poți folosi `python -m hui_indexer.cli` chiar dacă scriptul `hui` nu este găsit în PATH. Comenzile complete de import/export sunt în README și în protocolul de indexare.

## Reader din cod

Instalează Flutter **3.38.5**, Visual Studio cu componenta **Desktop development with C++** și Windows SDK. Activează Developer Mode pentru symlink-urile plugin-urilor. Verifică uneltele prin `flutter doctor -v`.

```powershell
python hui/scripts/prepare_reader.py
cd hui/app
flutter pub get
flutter test
flutter build windows --release
```

Rezultatul, numai după un build reușit, se află în `hui/app/build/windows/x64/runner/Release/`. Distribuie întregul director. Identitatea aplicației Flutter este separată de aplicația HistoryLab Android existentă.

În Reader apasă **Importă .hui**, alege pachetul și așteaptă verificarea. Biblioteca nu conține exemple importate automat. Deschide sursa, pagina și indicele pentru navigare în ambele sensuri. Pentru căutare exactă pe indicii canonici selectează **Indici documentați**, iar pentru legături alege **Relații explicite**.

## Artefacte CI

În Actions, deschide o rulare reușită **HUI Windows Reader** și descarcă `HUI-Reader-Windows`. Starea exactă a build-urilor efectiv executate este consemnată în `test_report.md`; documentația de compilare nu reprezintă singură dovada unui executabil produs.
