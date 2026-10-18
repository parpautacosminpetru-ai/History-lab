# historytool — raport de verificare tehnică

**Data:** 18 octombrie 2026  
**Versiune:** 1.0.1 operațională locală  
**Mediu de probă:** Python 3.13, FastAPI TestClient, SQLite FTS5, PyMuPDF, Tesseract (ron + eng), Chromium automatizat.  
**Rezultat:** 13 teste automate trecute / 13, plus flux vizual end-to-end Chromium fără erori JavaScript.

| Domeniu | Comportament verificat |
|---|---|
| Import | TXT în lot, fișier cu conținut SHA-256 identic nu este duplicat |
| Index | Lexeme, pasaje, afirmații textuale identice deduplicate |
| Navigare | Entități selectate, coapariții, pagini originale cu marcaj PDF |
| Precizie temporală | Secol/an/zi, dată lipsă, anul 44 î.Hr. și secolul II î.Hr. |
| Afirmații | Predicat literal obligatoriu; entitățile trebuie să fie în pasaj |
| Suprapunere | Intersecție între două regiuni, fără dublarea afirmației |
| Teme | Două etichete tematice pentru aceeași afirmație fără creare de duplicat |
| Laborator | Citat atașat unei note, export cu sursă și pagină |
| Citare | Bibliografie, cotă, pagină PDF vs. pagină tipărită VIII |
| OCR | PDF scanat generat local: text regăsit prin căutare, pagină redată |
| Integritate | SHA-256, arhivă ZIP cu fișiere și baza de date, jurnal |
| Eliminare | Sursă eliminată din index; atestările orfane curățate |
| Fundal | Indexare pornită asincron, verificare stare job |
| UI real | Import demo → indexare → căutare tag-uri → proiect notițe cu autosave |

## Corecții confirmate în v1.0.1
- Căutarea lexicală raportează totalul FTS și permite paginarea rezultatelor în loc să pretindă exhaustivitate din primele 2.500.
- Fuziunea manual confirmată a identităților conservă atestările, temele și afirmațiile verificate, inclusiv la coliziunea între înregistrări.
- Serverul local respinge cererile cu antete Host non-locale.
- Interfața nouă `historytool` a fost retestată prin Chromium.

## Ce NU a fost validat

- recuperarea exhaustivă a tuturor relațiilor semantice dintr-un corpus istoric real;
- rata de eroare OCR pe manuscrise și ediții dificile;
- scalabilitate certificată la sute de volume de mari dimensiuni;
- recunoaștere exhaustivă și dezambiguizare a persoanelor;
- aprobarea sau certificarea independentă de către cercetători istorici.

Acest document atestă teste efectuate asupra aplicației și este **diferit de un raport de validare științifică a rezultatelor istorice**.
