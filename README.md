# HistoryLab — Atlasul explicit

**Prototip Android gratuit, offline, cu indexare manuală și spațiu de lucru unic (timp + geografie).**

Acest depozit înlocuiește proiectul Android anterior. Conținutul vechi nu mai face parte din ramura `main`, dar **istoricul Git este păstrat**, astfel încât versiunile anterioare să poată fi recuperate.

## Principiul metodologic

- **Doar explicitul din sursă.** Aplicația nu produce inferențe, sinteze, cronologii inventate sau clasificări automate. Autorul bazei introduce și verifică fiecare informație.
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
7. **Import/export JSON** pentru arhivare și mutarea bazei între dispozitive. Importul verifică referințele și cere confirmarea înainte de a înlocui datele.

**Nu sunt incluse date istorice inventate sau exemple precompletate.** Baza pornește goală și se dezvoltă exclusiv prin înregistrările tale. Nicio funcție AI, niciun server de cont, nicio permisiune INTERNET.

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

IndexedDB are patru colecții:

| Colecție | Scop |
| --- | --- |
| `sources` | Identificarea bibliografică unică |
| `passages` | Text original + coordonate bibliografice, o singură dată |
| `entries` | Fișe de conținut și indexuri; `passageIds[]` leagă oricâte fragmente |
| `relations` | Legături între fișe și `passageId` care le justifică |

Arhiva JSON conține aceste patru tabele și formatul `historylab-explicit-1`. Editarea locală nu modifică fișierul de carte originar.

## Limite actuale

- Acesta este **un prototip funcțional**, nu o demonstrație că indexarea manuală este exhaustivă. Exhaustivitatea trebuie verificată separat de istorici pe surse reale.
- Harta arată geografia fizică modernă, nu hotare ale imperiilor sau hărți politice istorice gata făcute. Contururile și localizările istorice introduse manual trebuie documentate; nu se generează automat.
- Pentru intervale vechi, conversia lunilor/zilelor pe riglă este doar o **poziționare vizuală aproximativă**; aplicația nu convertește calendare istorice. Formulările datelor din surse se păstrează ca text exact.
- Legăturile genealogice pot fi reprezentate manual ca fișe și relații, dar nu există încă vizualizare automată de arbore genealogic.
- Pentru colecții foarte mari sunt necesare optimizări de indexare full-text, export în flux, control avansat al coliziunilor pe hartă și teste de performanță.
- Nu încărca în depozitul **public** scanări, pasaje protejate de drepturi de autor sau arhive private. Datele pe care le introduci în APK sunt stocate local și **nu sunt publicate în GitHub**. Arhivele JSON se salvează doar la comanda ta.
- Ștergerea datelor aplicației ori dezinstalarea poate elimina baza locală. Exportă periodic o copie JSON!

## Date geografice

Contururile de referință din `app/src/main/assets/world.geojson` provin din [johan/world.geo.json](https://github.com/johan/world.geo.json), pe baza datelor geografice [Natural Earth](https://www.naturalearthdata.com/) (domeniul public). Ele reprezintă **geografia terestră de referință**, nu teritorii istorice.

## Evoluții viitoare

Editare completă a fiecărui pasaj, relații genealogice vizuale, multipli autori cu poziții cartografice coexistente, date de mare precizie în calendare originale, statistici de acoperire a fiecărui paragraf, export academic și automatizări strict de vizualizare, fără interpretarea textelor.
