# Instalare și compilare Android

Reader este aplicație Flutter distinctă, pentru Android 8.0/API 26 sau mai nou. Indexer și OCR nu se instalează pe telefon: telefonul primește catalogul deja construit.

## APK

În Actions, deschide o rulare reușită **HUI Android APK** și descarcă artefactul `HUI-Reader-Android-debug`. Dezarhivează și transferă `app-debug.apk` pe telefon. Permite instalarea din sursa aleasă în setările dispozitivului. Este APK de test, semnat cu cheia debug, fără o cheie stabilă de distribuție academică.

Pentru compilare locală: instalează Flutter 3.38.5, JDK 17 și Android SDK; acceptă licențele necesare și verifică `flutter doctor -v`.

```sh
python hui/scripts/prepare_reader.py
cd hui/app
flutter pub get
flutter build apk --debug
```

Fișierul rezultat este `hui/app/build/app/outputs/flutter-apk/app-debug.apk`. Workflow-ul verifică efectiv permisiunile APK-ului cu `aapt dump permissions`. Nu se livrează o variantă care cere rețea pentru cercetare.

## Transferul colecției

1. În Indexer publică și exportă `.hui`.
2. Transferă pachetul prin USB sau alt mecanism ales de tine.
3. În Reader apasă **Importă .hui**. Selectorul de fișiere poate afișa servicii ale sistemului Android; HUI nu cere cont sau cloud.
4. După import, oprește Wi-Fi și datele mobile. Aceeași colecție se poate căuta și naviga local.
5. Originalele se deschid numai dacă sunt incluse legal în pachet. Într-un pachet doar cu index, lipsa scanării este indicată explicit.

Limita actuală Reader este 256 MiB per pachet. Pentru pachete mai mari este necesară dezvoltarea importului în flux. Nu dezinstala aplicația și nu șterge datele ei înainte să ai o copie a pachetului original.

`integration_test/reader_flow_test.dart` poate fi rulat pe un dispozitiv de test prin `flutter test integration_test/reader_flow_test.dart -d ID`. Harness-ul Flutter necesită o configurație temporară de debug cu permisiune de loopback; workflow-ul de integrare pregătește această variantă separat și dezactivează Wi-Fi și datele mobile înainte de test. Această configurație nu este folosită de workflow-ul APK distribuit.
