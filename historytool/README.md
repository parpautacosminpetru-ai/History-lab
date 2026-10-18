# historytool — ediție locală operațională 1.0

**Stație de cercetare istorică locală, cu index universal, trimiteri la surse, suprapuneri documentare validate și laborator de sinteză.** Nu este un serviciu online, o machetă sau un sistem de generare de afirmații istorice. Codul rulează local, iar sursele rămân pe calculator.

## Pornire imediată

1. Instalează **Python 3.11 sau mai nou**, dacă nu îl ai deja. La Windows, bifează „Add Python to PATH” în timpul instalării.
2. Dezarhivează folderul `historytool` într-un loc în care ai drept de scriere, de exemplu `Documente/historytool`.
3. **Windows:** dublu-clic pe `start_windows.bat`. **macOS/Linux:** deschide un terminal în folder și execută `sh start_mac_linux.sh`.
4. Prima pornire instalează automat dependențele într-un mediu privat `.venv` și necesită internet. La pornirile următoare nu mai este necesară instalarea.
5. În browser se deschide **http://127.0.0.1:8765**. Dacă nu se deschide automat, introdu manual adresa.
6. Pentru oprire închide terminalul sau apasă `Ctrl+C`.

### Fișiere acceptate

PDF cu text selectabil, PDF scanat cu OCR opțional, DOCX, TXT (UTF-8) și MD. Limita pe fișier: **100 MB**; maximum **100 fișiere per lot**. Poți încărca oricâte loturi, în limita stocării și a puterii calculatorului. **Nu există o garanție de performanță pentru un număr arbitrar de cărți**.

### OCR pentru PDF scanate

Instalează separat [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) și pachetele de limbă `ron` și, opțional, `eng`. Bifează „OCR pentru PDF scanate” înainte de indexare. Se prelucrează automat paginile fără text selectabil. Rezultatul OCR este **o transcriere neverificată** și trebuie comparat cu imaginea originală. Dacă OCR lipsește sau eșuează, programul semnalează pagina; nu inventează textul.

## Flux de lucru real

### 1. Index universal și dovezi

- Apasă **Atașează fișiere** și încarcă sursele din bibliografia proprie.
- Apasă **Indexează sursele**. Operația rulează în fundal, iar biblioteca salvează documentele originale și hash-ul SHA-256 pentru controlul integrității.
- Indexul automat reține toate cuvintele din textul extras, pasaje, afirmații formulate textual identic, apariții de nume candidate și trimiteri originale. Documente binar identice nu se dublează.
- Selectează un nume/termen. Vei vedea toate aparițiile recunoscute, iar un clic deschide pasajul exact. **Coaparițiile automatizate sunt afișate separat și nu sunt prezentate drept relații istorice.**
- În vizualizatorul de pasaj poți înregistra o **afirmație explicită verificată**: subiect din pasaj, formularea literală a predicatului, obiect, loc și temă facultative. API-ul respinge formulări absente din fragment și elemente fără apariții indexate. Validarea semantică finală aparține istoricului.
- Afirmațiile confirmate apar ca **casete imbricate în cadrul documentar comun**, inclusiv în intersecția a două regiuni când se justifică prin aceeași atestare. Nu există grafuri artificiale cu săgeți și nu sunt generate hărți geografice fără surse.
- Poți adăuga manual entități candidate, confirma identități sau verifica forme alternative de nume. Persoanele omonime NU trebuie unite înainte de verificarea istoricului.
- **Rigla universală** permite navigarea pe trepte mari până la ani, luni și zile. Înregistrările cu dată incompletă rămân nedeterminate pentru selecțiile mai precise; anul 1475 nu devine automat o anumită zi. Sunt recunoscute și expresii uzuale `î.Hr.`. Convențiile calendaristice și cronologiile speciale trebuie evaluate separat.

### 2. Interogare

- Intră în **Interogare**; inițial apare doar bara de căutare.
- Scrie termeni sau o întrebare. Apare o casetă cu **tag-uri** și trimiteri către sursele din corpus; apăsarea pe un tag deschide pasajul exact.
- Poți adăuga până la cinci **teme paralele**, evidențiate în culori distincte. Căutarea este în prezent **lexicală, cu scor de potrivire**, nu un motor universal de răspunsuri semantice certificate. Niciun răspuns nu este fabricat dacă nu există dovadă.

### 3. Laboratorul istoricului

- Creează un **proiect de cercetare**, redactează propria analiză și atașează fragmente verificate din index sau interogare.
- **Salvarea automată** protejează schița în timpul redactării; există și buton manual de salvare.
- Exportul Markdown conține textul autorului și trimiterile către surse. Dacă ai completat autorul/ediția/cota și numerotarea tipărită, acestea apar în citări.

## Proveniență și bibliografie

Fiecare sursă poate avea **autor/editor, titlu bibliografic, publicare, ediție/volum, cotă arhivistică, limbă, observații**. Din biblioteca din stânga apasă simbolul **✎** al sursei. În cititor poți salva manual **pagina tipărită** pentru fiecare pagină PDF.

**Atenție:** „PDF p. 8” înseamnă pagina fizică 8 din fișier, nu neapărat pagina tipărită 8. Pentru DOCX și TXT se folosesc segmente virtuale: ele nu echivalează cu paginarea ediției originale.

## Date, verificare și siguranță

- Date active: `data/atlas.sqlite3` (SQLite) și `data/sources/` (originale). Fișierele sursă sunt copiate cu nume bazate pe SHA-256 și nu sunt modificate la afișarea marcajelor.
- **Copie de siguranță**: din interfață descarcă un ZIP cu baza de date, fișiere originale și manifest. Salvează-l separat de calculator.
- **Verifică integritatea surselor**: compară SHA-256 al fișierelor locale cu valoarea de la import. Aceasta verifică identitatea binară, nu calitatea OCR.
- **Jurnal**: păstrează evenimente precum importul, indexarea, validarea afirmațiilor și modificările bibliografice.
- Când elimini o sursă, aplicația o scoate din index și mută originalul în `data/trash/` în loc să-l distrugă imediat. Poate fi reimportată.
- Pentru **restaurare**, oprește aplicația, apoi extrage folderul `data/` din copia ZIP peste folderul din aplicație. Fă înainte o copie a datelor existente. Programul încearcă să repare referințele la original dacă a fost mutat în alt director.
- Serverul ascultă **doar** pe `127.0.0.1`. Nu configura port-forwarding și nu îl expune pe internet fără autentificare și măsuri suplimentare.

## Ce nu trebuie confundat cu o certificare istoriografică

1. **Indexarea semantică exhaustivă în sensul definit de proiect nu este demonstrată.** Indexarea lexicală acoperă textul extras. Entitățile, sinonimele și afirmațiile semantice echivalente pot necesita verificare și adnotare manuală; nu există garanție „zero omisiuni”.
2. **Un pasaj nu demonstrează automat o relație istorică.** Coaparițiile rămân separat etichetate. Relațiile verificate sunt înregistrate explicit de cercetător și păstrează dovada.
3. **OCR-ul poate greși**, în special la grafii istorice, caractere speciale, copii de slabă calitate și manuscrise. Este necesară verificarea pe facsimil.
4. **Suprapunerile reprezintă informația documentată**, nu o simulare obiectivă a întregii realități trecute. Regiunile nu sunt poligoane geografice validate.
5. **Datele istorice, calendarele vechi, identitățile ambigue și autoritatea surselor** necesită evaluare critică. Programul nu înlocuiește istoricul.
6. **Nu a avut loc încă o certificare academică independentă** sau o evaluare formală pe un corpus istoric mare, adnotat de experți.

## Teste de acceptanță

În mediul de dezvoltare, au trecut **13 teste automate** (`python -m pytest tests -q`), inclusiv generarea și OCR-ul unui PDF scanat, exportul bibliografic, atestări exact citate și respingerea formulărilor neprezente în sursă. Au trecut și verificări ale fluxului UI într-un browser Chromium (import demonstrativ, indexare, metadate, căutare, salvare automată). Vezi `RAPORT_TESTE.md`.

Pentru a rerula testele pe calculatorul tău: după pornirea inițială, instalează pachetele de test în `.venv` (`python -m pip install pytest httpx Pillow`, folosind Python din `.venv`), apoi `python -m pytest tests -q`.

**Versiune:** 1.0.1 operațională de lucru · 18 octombrie 2026 · utilizare locală, fără servicii AI externe.

## GitHub și confidențialitate

Codul nu include sursele istorice personale, baza de date sau notițele cercetătorului. `data/` este exclus din Git. Nu încărca niciodată documente private în repository-uri publice.

Instalarea locală este obligatorie: nu există un server public care să execute aplicația pentru tine.

## Interogări voluminoase

Rezultatele sunt paginate, cu numărul total al potrivirilor lexicale raportat de motor. Apasă „Afișează următoarele trimiteri” pentru a continua în întregul corpus. Potrivirile lexicale NU reprezintă automat interpretare semantică.
