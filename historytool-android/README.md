# historytool Android — build instalabil

Aplicația Android include interfața originală historytool și motorul local Python/FastAPI, lansate pe telefon, în procesul Android, pe `127.0.0.1:8765`.

## Funcții
- Import din memoria telefonului: PDF-uri cu text selectabil sau scanate, DOCX, PNG, JPG, TXT, MD.
- Index universal lexical, fără duplicarea fișierelor binar identice; păstrează citările exacte și originalele în memoria privată Android.
- Căutare cu tag-uri și rezultate paginate, riglă temporală cu precizia extrasă din text.
- Cadru comun cu afirmații verificate explicit de cercetător, nu relații deduse automat.
- Laborator de sinteză cu notițe, dovezi și export local; backup ZIP cu datele.
- PDF: pypdf extrage text; Android PdfRenderer afișează pagina originală. Citatul este evidențiat în inspector, NU pretindem evidențiere geometrică exactă pe imagine în această versiune.

## Limitări importante
- **OCR local pentru PDF-uri și imagini scanate folosește un model Latin încorporat.** Rezultatele OCR sunt neverificate și pot conține erori, mai ales pe pagini vechi sau deteriorate. Dacă nu este recunoscut textul, aplicația semnalează explicit acest lucru.
- Indexarea este lexicală/deterministă, **nu exhaustivă semantic**.
- Pe Android, performanța depinde de RAM și numărul de PDF-uri; nu s-a validat încă un corpus de sute de mii de pagini.
- APK-ul de debug permite instalare laterală pe propriul dispozitiv. Pentru distribuție publică este necesară semnare release și test pe dispozitive multiple.

## Construcție
Gradle 8.11.1, Android SDK 35 și JDK 17:

```bash
gradle --no-daemon :app:assembleDebug
```

APK-ul apare în `app/build/outputs/apk/debug/app-debug.apk`.

Motor original: `historytool` ediție locală 1.0.2. Adaptorul Android înlocuiește dependența PyMuPDF cu pypdf și Android PdfRenderer și citește DOCX din OpenXML fără lxml.

## Confidențialitate
Originalele și baza de date SQLite sunt stocate doar în memoria privată a aplicației. Motorul ascultă exclusiv pe loopback. `INTERNET` este necesar pentru conexiunea WebView la serverul local, nu pentru transmiterea surselor în cloud. Nu există autentificare de rețea; nu expune serverul pe internet.

## Actualizări Android
APK-urile debug din construcții diferite pot avea semnături diferite. Nu dezinstala o versiune care conține documente importante fără exportul anterior al datelor. Pentru actualizări stabile este necesară semnarea de distribuție cu o cheie persistentă.
