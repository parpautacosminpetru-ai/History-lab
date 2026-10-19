# HistoryLab — Atlasul explicit

**Prototip Android gratuit, offline, cu fotografie a paginii, OCR local pentru transcriere și indexare semantică integral manuală, într-un singur spațiu de lucru (timp + geografie).**

Acest depozit înlocuiește proiectul Android anterior. Conținutul vechi nu mai face parte din ramura `main`, dar **istoricul Git este păstrat**, astfel încât versiunile anterioare să poată fi recuperate.

## Principiul metodologic

- **Doar explicitul din sursă.** Aplicația nu produce inferențe, sinteze, cronologii inventate sau clasificări automate. OCR-ul recunoaște mecanic litere, însă autorul bazei verifică fidelitatea transcrierii și decide fiecare indice.
- **O singură înregistrare canonică.** Sursele, pasajele transcrise și fișele de informație sunt stocate separat, cu identificatori proprii. Un pasaj poate susține mai multe fișe, iar o fișă poate avea mai multe pasaje din surse diferite. Același pasaj nu este salvat de două ori dacă sursa, localizarea și textul coincid.
- **Indexări multiple, fără duplicate fizice.** O fișă are oricâte teme, actori, termeni și alte metadate. Căutarea citește aceleași date, fără a crea copii tematice.
- **Revenire la sursă fără răsfoire.** Fiecare pasaj are sursă, capitol, pagini, paragraf, propoziție și rând; citatul original este afișat lângă informație.
- **Ordine originală + acces neliniar.** Consultă fișele după cronologie sau după autor/sursă/pagină, căutând în același timp în toate câmpurile.

## Ce poți folosi în versiunea aceasta

1. **Harta lumii permanentă**, offline, cu geografie de referință modernă. Panoramare, zoom, centrare pe Europa sau glob. Punctele se pot introduce numeric sau prin atingerea hărții. Contururile manuale se desenează direct pe hartă, numai când sunt susținute de surse. Suprapunerile în același punct se grupează selectabil.
2. **Rigla cronologică permanentă**, cu scări de la milenii și secole până la luni, derulare și zoom. Ani înainte/după Hristos fără anul 0; textul sursei păstrează datele istorice exact cum sunt formulate. Periodizările apar numai dacă au fost documentate ca fișe cu autor și fragment, putând coexista opinii diferite.
3. **Catalog de surse** (titlu, autor, specializare, ediție, an, referință bibliografică).
4. **Fișă manuală** cu text original, capitol, interval de pagini, paragraf, propoziție, rând, parafrază opțională, an sau interval, loc, coordonate, actori, teme, termeni și geometrie.
5. **Dovezi multiple per fișă**, inclusiv legarea unui fragment existent, și **relații explicite între fișe** cu fragmentul care le justifică. Relațiile cu puncte geografice sunt suprapuse peste hartă.
6. **Căutare universală și filtrare** după tip, sursă, timp, text, termeni, autor. Lista fișelor și detaliile apar peste hartă, fără navigare într-o aplicație separată.
7. **Atelier OCR pe textul original:** fotografie sau imagine din galerie, OCR local inclus în APK (limbile cu alfabet latin), imagine originală afișată lângă transcrierea editabilă, verificare manuală, selecție exactă, completarea indexurilor și „Salvează și continuă”. Sursa, capitolul și pagina rămân setate până la următoarea fotografie.
8. **Import/export JSON** pentru arhivare și mutarea bazei între dispozitive, inclusiv imaginile paginilor (arhivele pot deveni mari). Importul verifică referințele și cere confirmarea înainte de a înlocui datele.

**Nu sunt incluse date istorice inventate sau exemple precompletate.** Baza pornește goală și se dezvoltă exclusiv prin înregistrările tale. Modelul OCR inclus în APK doar recunoaște textul; nu decide indexuri sau interpretări. Nu există server de cont și nu este cerută permisiunea INTERNET.

## Lucrul direct pe textul original (mod rapid)

1. Înregistrează o lucrare în **Surse → ＋ Sursă**.
2. Apasă **▧ Atelier OCR**. Alege lucrarea, introdu capitolul și pagina, apoi apasă **Fotografiere** sau **Din galerie**.
3. Aplicația păstrează **fotografia originală nemodificată**, în stocarea privată, și pune alături transcrierea prin OCR local. Corectează diferențele față de imagine, apoi confirmă **„Am confruntat transcrierea cu fotografia”**.
4. Selectează direct din transcriere propoziția/sintagma și apasă **„Preia selecția”**. Fragmentul exact devine citat; eticheta pentru regăsire se umple mecanic cu începutul selecției, fără interpretare.
5. Completează **numai** indexurile, actorii, tema, locul, anul și eventual paragraf/propoziție/rând (dacă sunt explicit susținute); apasă **„Salvează și continuă”**. Fișa nouă va avea automat sursa, capitolul, pagina și legătura către fotografia originală.
6. Repetă selecția pentru toate informațiile explicite. Nu reintroduce sursa/capitolul/pagina. Apasă **Pagina +1** când fotografiezi următoarea pagină.
7. Din detaliul unei fișe deschide **„Vezi fotografia paginii originale”** ca să verifici contextul vizual.

**Important:** OCR-ul nu este echivalent cu textul original; îl compari cu fotografia înainte să-l folosești ca citat exact. De aceea fotografia nu este modificată automat. Recunoașterea se face cu **Google ML Kit Text Recognition (model local inclus în APK)**, fără upload și fără analiză semantică. Dacă folosești interfața în browser, fără învelișul Android, fotografia poate fi afișată și transcrisă manual, dar nu există OCR automat.

Fotografiile brute sunt păstrate ca fișiere locale; exportul JSON include copii codificate ale imaginilor, astfel încât o arhivă exportată poate fi mult mai mare decât baza textuală. Pentru volume foarte mari vor fi utile ulterior arhive separate pentru imagini și catalog.

## Instalarea APK-ului

1. În GitHub, deschide **Actions → HistoryLab · APK offline**.
2. Alege ultimul workflow reușit de pe `main`.
3. Sub **Artifacts**, descarcă `HistoryLab-Atlasul-Explicit-Android-APK`.
4. Dezarhivează, transferă `app-debug.apk` pe dispozitivul Android și instalează-l. Poate fi necesar să permiți instalarea din această sursă în setările Android.

APK-ul este **debug**, potrivit testelor personale, nu o versiune semnată pentru distribuție publică. Necesită Android 8.0 sau mai nou.

## Pornire în browser pentru verificare

Din rădăcina proiectului:

```sh
python3 -m http.server 8080 --directory app/src/main/assets
```

Deschide apoi `http://localhost:8080` (IndexedDB funcționează pe `localhost`).
Pentru testele modelului de date, rulează `npm test`.
Pentru compilare locală Android, instalează JDK 17, Android SDK 35 și Gradle 8.11.1, apoi rulează `gradle :app:assembleDebug`.

## Modelul bazei de date

IndexedDB are cinci colecții:

| Colecție | Scop |
| --- | --- |
| `sources` | Identificarea bibliografică unică |
| `passages` | Text original + coordonate bibliografice, o singură dată |
| `entries` | Fișe de conținut și indexuri; `passageIds[]` leagă oricâte fragmente |
| `relations` | Legături între fișe și `passageId` care le justifică |
| `pages` | Fotografie originală, transcriere OCR corectabilă și confirmarea verificării |

Arhiva JSON conține cele cinci tabele și formatul `historylab-explicit-1` (arhivele vechi fără colecția `pages` rămân compatibile). Editarea locală nu modifică fișierul de carte originar.

## Limite actuale

- Acesta este **un prototip funcțional**, nu o demonstrație că indexarea manuală este exhaustivă. Exhaustivitatea trebuie verificată separat de istorici pe surse reale.
- Harta arată geografia fizică modernă, nu hotare ale imperiilor sau hărți politice istorice gata făcute. Contururile și localizările istorice introduse manual trebuie documentate; nu se generează automat.
- Pentru intervale vechi, conversia lunilor/zilelor pe riglă este doar o **poziționare vizuală aproximativă**; aplicația nu convertește calendare istorice. Formulările datelor din surse se păstrează ca text exact.
- Legăturile genealogice pot fi reprezentate manual ca fișe și relații, dar nu există încă vizualizare automată de arbore genealogic.
- Pentru colecții foarte mari sunt necesare optimizări de indexare full-text, export în flux (imaginile măresc arhiva), control avansat al coliziunilor pe hartă și teste de performanță.
- Nu încărca în depozitul **public** scanări, pasaje protejate de drepturi de autor sau arhive private. Datele pe care le introduci în APK sunt stocate local și **nu sunt publicate în GitHub**. Arhivele JSON se salvează doar la comanda ta.
- Ștergerea datelor aplicației ori dezinstalarea poate elimina baza locală. Exportă periodic o copie JSON!

## Date geografice

Contururile de referință din `app/src/main/assets/world.geojson` provin din [johan/world.geo.json](https://github.com/johan/world.geo.json), pe baza datelor geografice [Natural Earth](https://www.naturalearthdata.com/) (domeniul public). Ele reprezintă **geografia terestră de referință**, nu teritorii istorice.

## Evoluții viitoare

Editare completă a fiecărui pasaj, relații genealogice vizuale, multipli autori cu poziții cartografice coexistente, date de mare precizie în calendare originale, statistici de acoperire a fiecărui paragraf, export academic și automatizări strict de vizualizare, fără interpretarea textelor.
