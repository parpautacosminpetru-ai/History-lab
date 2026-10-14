# HistoryLab

**Atelier digital personal pentru cercetarea istorică • Android • offline • fără AI generativ**

Proiect nou, construit de la zero. Istoricul deține controlul asupra clasificării, verificării, adnotărilor, interpretărilor, sintezei și redactării. Aplicația execută doar operații documentare și reguli definite de utilizator.

> **Stadiu: prototip Android v0.2, cu noua interfață de atelier; APK-ul trebuie compilat și verificat pe un dispozitiv.** Construcția APK este configurată în GitHub Actions.

## Ce este implementat în v0.2

- Arhivă locală inițial goală: fotografiere prin aplicația de cameră sau import de imagini existente.
- Imaginea este copiată **octet cu octet**, fără retușare, în spațiul privat al aplicației. SHA-256 identifică fișierul original.
- Metadate completate de istoric: tip, autor, dată, localitate, proveniență/referință, fragmentaritate.
- Vizor cu zoom la gesturi; fotografia rămâne vizibilă alături de OCR și de notele cercetătorului.
- OCR optic local **Tesseract**, pornit automat după arhivarea fotografiei (inițial română și engleză, incluse în APK la construire); model lingvistic suplimentar `.traineddata` importabil local.
- OCR brut separat de transcrierea revizuită de istoric; recunoașterea nu marchează singură textul drept verificat.
- Jurnal al rulărilor OCR și al editărilor de metadate, transcrieri și fișe.
- Indexare mecanică prin reguli definite de utilizator: **axă + etichetă + expresie de căutat**. Intersecții între axe din apariții literale.
- Căutare locală, acces la sursa originală și evidențieri ale unor cuvinte bazate pe coordonatele OCR (unde acestea există).
- Adnotări și întrebări proprii, cu status „de verificat”, legate de fiecare sursă.
- Fișe de sinteză și capitole scrise exclusiv de istoric; legături explicite către sursele utilizate.
- Referințe bibliografice orientative, formate strict din metadatele introduse, fără inventarea câmpurilor lipsă.
- Export fișe ca `.txt` și copie de siguranță `.zip` cu datele și fișierele originale.
- **Fără permisiune INTERNET** în aplicație; fără server, cont, cloud, generare de argumente sau redactare autonomă.

## Important: sensul expresiei „fără AI”

HistoryLab **nu folosește AI generativ** pentru a crea concluzii, texte istorice, interpretări sau surse. Motorul Tesseract include însă tehnici de recunoaștere statistică/antrenată (inclusiv modele LSTM); ar fi inexact să afirmăm că OCR-ul este exclusiv algoritmic clasic în toate componentele sale. Rezultatele OCR pot conține erori. În schimb, **clasificarea și indexarea din HistoryLab sunt reguli explicite, reproductibile**, definite de utilizator, fără clasificare semantică automată. Aplicația nu corectează și nu rescrie singură sursele.

## Construirea APK pe GitHub (fără să programezi)

1. Deschide depozitul tău GitHub `History-lab` (deja creat).
2. Încarcă toate fișierele acestui proiect păstrând structura directoarelor. Dacă ai conectat GitHub la ChatGPT, poți solicita încărcarea codului după ce există depozitul și accesul aplicației GitHub este permis.
3. Intră în depozit la **Actions → APK Android - HistoryLab** și rulează **Run workflow** (sau lasă-l să ruleze automat la `push`).
4. După un build reușit, deschide rularea → **Artifacts → HistoryLab-android-debug-apk**. Descarcă arhiva, extrage `app-debug.apk` și instalează pe telefon pentru test.
5. Un APK de tip *debug* este pentru testare, nu pentru publicare în Google Play. Pentru versiunea finală va trebui configurată semnarea release.

**Buildul GitHub are nevoie de internet** ca să obțină Gradle, librăriile și modelele OCR. **Aplicația instalată nu are nevoie de internet** pentru funcțiile v0.1.

Pentru build local, sunt necesare Java 17, Gradle 8.11.1, Android SDK 35 și o conexiune de build pentru dependențe:

```bash
bash scripts/fetch_ocr_models.sh
gradle :app:assembleDebug
```

Teste pentru regulile deterministe (necesită doar Java):

```bash
mkdir -p /tmp/historylab-tests
javac -d /tmp/historylab-tests app/src/main/java/ro/historylab/IndexMatcher.java app/src/main/java/ro/historylab/CitationFormatter.java tests/EngineTest.java
java -cp /tmp/historylab-tests EngineTest
```

## Interfața atelierului v0.2

- **Atelier**: ecran de start cu acces direct la cameră/import, indicatori reali de progres (surse, transcrieri neverificate, fișe), ultimele documente și scurtături interactive.
- **Arhivă vizuală**: documente în carduri cu miniatura originalului, metadate și starea verificării; filtrele „Toate”, „De verificat”, „Verificate”, „Fragmente”.
- **Cronologie**: doar sursele cu data introdusă manual. Sunt ordonate numai datele ce încep cu un an de 4 cifre, după acel prim an; restul rămân într-o secțiune separată, fără datări ghicite și fără asociere de evenimente.
- **Identitate vizuală**: paletă cerneală, fildeș/pergament și auriu; titluri serif și navigare cu 5 secțiuni.
- Interacțiunile conduc la funcții reale: fotografiază, importă, caută literal, definește reguli, redactează fișe și exportă datele.

## Fluxul de lucru

```text
Fotografie / import document
           │
           ├────> ORIGINAL IMUTABIL + SHA-256
           │             │
           │             └────> „Deschide sursa” / zoom
           │
           └────> OCR OPTIC BRUT (neverificat)
                          │
                          ├────> transcriere revizuită de istoric
                          │
                          └────> reguli explicite (axă, etichetă, expresie)
                                       │
                                       ├──> index și intersecții
                                       └──> căutare / pasaj / original

ISTORICUL ──> marginalii / întrebări ──> fișă de sinteză ──> redactare și export
```

### Exemplu Bacău

1. Importă o fotografie de document și înregistrează proveniența.
2. OCR-ul română + engleză (`ron+eng`) pornește automat după salvarea sursei. Verifică și corectează transcrierea.
3. Adaugă regula: **Localitate** / **Bacău** / expresie **Bacău**.
4. Intră în „Index” și deschide lista de documente cu această expresie. Apasă pe document pentru a vedea fotografia și marcajele OCR.
5. Creează o fișă și atașează documentul. Explicația istorică o scrii tu.

## Ce NU este încă gata

- Import multipagină PDF/TIFF, import în masă, interoperabilitate TEI-XML și Zotero.
- OCR garantat pentru orice limbă/scriere; în special scrierile vechi, chirilice sau manuscrisele au nevoie de modele suplimentare și verificare paleografică.
- Vizor de captură cu lupă integrată; în această versiune zoom-ul de captură depinde de aplicația telefonului, iar zoom-ul de lectură este inclus.
- Adnotare de regiuni prin desen manual pe imagine; în prezent marcajele din imagine sunt coordonate OCR estimate.
- Căutare morfologică/semantică: intenționat **nu** există inferență semantică automată.
- Hărți istorice georeferențiate și cronologie avansată cu gestionarea incertitudinii rămân prevăzute în foaia de parcurs. Există acum o cronologie elementară, bazată exclusiv pe metadatele istoricului.
- Restaurarea din arhiva `.zip` (exportul funcționează, dar restaurarea este etapă viitoare).
- Editor complet de carte/monografie, paginare academică, gestionarea tuturor stilurilor de citare și export DOCX/PDF.
- Criptarea locală și a exporturilor. Spațiul este privat aplicației Android, dar arhivele `.zip` exportate nu sunt criptate.
- Testare pe telefon fizic și certificarea accesibilității; prototipul trebuie verificat înainte de folosire pentru un proiect academic real.

## Principii academice

1. Originalul nu se editează. Orice prelucrare este separată de fotografia primară.
2. Datele necunoscute rămân necunoscute. Nu se inventează autor, loc, dată, cotă sau context.
3. OCR-ul este marcat neverificat până când istoricul confirmă o transcriere.
4. Potrivirile din index indică prezența expresiei, nu adevărul, cauza ori sensul unei afirmații.
5. Sintezele, întrebările, comentariile și deciziile aparțin istoricului.
6. Operațiunile documentare sunt trasabile prin jurnal și legături către sursă.

## Organizarea proiectului

- `app/src/main/java/ro/historylab/HistoryDb.java`: structura arhivei SQLite.
- `OcrEngine.java`: recunoaștere optică locală Tesseract și casete de cuvinte.
- `IndexMatcher.java`: potriviri literale Unicode; fără clasificare interpretativă.
- `ZoomImageView.java`: vizor cu zoom și marcaje OCR.
- `MainActivity.java`: interfață Android în română.
- `BackupExporter.java`: export manifest JSON + imagini originale în ZIP.
- `CitationFormatter.java`: compunerea mecanică a referinței.
- `.github/workflows/android-apk.yml`: configurare alternativă pentru producerea APK-ului de test în cazul în care există drepturi de publicare a workflow-urilor.
- Fluxul `historylab-init.yml` publicat în GitHub poate compila APK-ul la actualizarea arhivei sursă; fișierele workflow noi nu sunt publicate de token-ul GitHub Actions.
- `PLAN.md`: dezvoltare etapizată.

### Biblioteci externe

- [Tesseract4Android](https://github.com/adaptech-cz/Tesseract4Android) (Apache-2.0).
- [Tesseract OCR / tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast) (licența și condițiile proiectului sursă).
- AndroidX Core (Apache-2.0).

**Drepturile asupra acestui proiect:** nu se acordă aici o licență publică de reutilizare. Dacă decizi să-l publici ca software liber sau comercial, alege explicit licența și verifică obligațiile licențelor dependențelor.

Modelele OCR incluse în build sunt fixate la tag-ul `4.0.0` din `tessdata_fast`, pentru a evita schimbarea lor necontrolată între builduri.

### Teste cronologie

`javac -encoding UTF-8 -d /tmp/historylab-tests app/src/main/java/ro/historylab/TimelineOrder.java tests/TimelineOrderTest.java && java -cp /tmp/historylab-tests TimelineOrderTest`
