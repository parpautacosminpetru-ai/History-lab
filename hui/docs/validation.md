# Validare și criterii

Testele nu utilizează cărți comerciale. Documentele demonstrative sunt produse de `hui_indexer.demo` și includ avertismentul că sunt texte sintetice, fără afirmații istorice. Aprobările din fixture sunt etichetate drept validare de test.

| Test cerut | Verificare implementată |
| --- | --- |
| 1. Text și pagină | Import PDF, FTS „domnie”, pagina PDF 2 și fișierul original identic |
| 2. Pagină și evidențiere | Casetele intersectează efectiv literele rasterizate; teste CropBox și 0/90/180/270°; widget Reader |
| 3. Navigare inversă | Proveniență SQL și test widget sursă → pagină → indice → apariție → bibliotecă |
| 4. Negație | Respingere pozitivă și interogare care exclude explicit relațiile negate |
| 5. Modalitate/atribuire | Respingerea certitudinii și a eliminării vocii atribuite |
| 6. Recurență | Un indice, trei surse, trei apariții și proveniențe |
| 7. Suprapuneri | Intervale suprapuse și multipagină fără duplicarea textului |
| 8. Omonime | Aceeași etichetă produce ID-uri distincte până la alegerea explicită |
| 9. Limbi | Română/franceză/germană, OCR englezesc, variante validate/nevalidate, Unicode suplimentar |
| 10. Offline | Interzicerea rețelei în testele Python/Dart; workflow Android cu Wi-Fi/date oprite |
| 11. Reader fără AI | Catalog read-only, verificare cod fără client de inferență, permisiuni APK auditate |
| 12. Incremental | Hash deduplicat, ediție nouă pentru fișier schimbat, reluare fără schimbarea ID-urilor |
| 13. Hash | Corupere intenționată respinsă; versiunea activă rămâne disponibilă |
| 14. Acoperire | Pagini complete de procesare, zero sau puține caractere confirmate; semantică declarată nemăsurată |
| 15. Securitate | Traversări de căi, ZIP invalid, schema SQL necunoscută, SQL neîncrezut și propuneri AI invalide |

Existența unui test în cod nu înseamnă că a fost executat pe fiecare platformă. Rezultatele efectiv obținute și rulările CI sunt în `test_report.md`.

Verificarea automată validează localizarea, integritatea și câteva reguli conservatoare. Nu certifică adevărul istoric sau echivalența semantică. Confirmările umane sunt jurnalizate distinct; coordonatele corecte nu schimbă automat starea unui indice în „Confirmat uman”.

## Reproducere

```sh
python -m pip install -e 'hui/indexer[test]'
python -m pytest hui/indexer/tests -q
npm test
python hui/scripts/prepare_reader.py
cd hui/app
flutter pub get
flutter analyze --no-fatal-infos
flutter test --reporter expanded
```

`python hui/scripts/generate_fixtures.py` regenerează documentele originale, pachetul și vectorii de interogare. Dacă se schimbă schema, sincronizează și copiile ei înainte de testarea Reader. Publicarea unei versiuni noi de schemă trebuie însoțită de o migrare și de teste de compatibilitate; versiunea 0.1 acceptă numai schema 1.
