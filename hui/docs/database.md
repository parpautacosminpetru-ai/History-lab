# Baza de date

Schema canonică este `indexer/src/hui_indexer/migrations/001_initial.sql`. Copiile din `schemas/index_schema.sql` și `app/assets/schema.sql` trebuie să fie identice. `PRAGMA user_version=1` identifică prima schemă; versiunile ulterioare sunt respinse până la implementarea migrării lor. Inițializarea este tranzacțională și cheile externe sunt active.

| Entități | Rol |
| --- | --- |
| Sources, Authors, SourceAuthors | Lucrare și autori cu ordinea bibliografică |
| SourceEditions | Ediție și original asociat, hash, progres |
| Pages | Numerotare PDF/tipărită, geometrie, text brut și imagine |
| DocumentStructures | Structuri cu părinți și intervale; detecțiile sunt propuneri |
| TextSegments, TextBoxes | Text exact și coordonate stand-off |
| IndexNodes, NodeVariants | Identități distincte și echivalențe validate |
| EvidenceSpans, SpanParts | Intervale suprapuse și multipagină, fără copiere de text |
| Occurrences | Legături indice → dovezi |
| ExplicitRelations, RelationEvidence | Afirmații cu modificatori și dovezi multiple |
| ReviewLog, Issues | Decizii umane, incertitudini și probleme |
| ProcessingJobs, IndexVersions | Reluare și versiuni publicate |

## Text și coordonate

Textul extras este păstrat integral în `Pages.raw_text`. Segmentele sunt intervale exacte în acest text. În versiunea 0.1 există câte un segment pentru fiecare pagină cu text. `normalized_text` este separat și nu înlocuiește originalul.

Intervalele sunt `[start,end)`, în **puncte de cod Unicode**, nu octeți, tokenuri sau unități UTF-16. SQLite `substr` începe de la 1; Python și API-ul HUI încep de la 0. Flutter convertește explicit între pozițiile UTF-16 ale selecției și punctele de cod.

`TextBoxes` folosește coordonate normalizate `[0,1]`, origine în colțul stânga-sus al paginii afișate. Conversia PDF → imagine folosește `FPDF_PageToDevice`, aplicând CropBox și rotația intrinsecă exact ca randarea. Rasterul de referință și dreptunghiurile sunt mărite/rotite împreună în Reader; în pdfrx coordonatele sunt proiectate în `pageRect`. Pentru OCR, dreptunghiurile sunt ale cuvintelor, astfel încât selectarea unui fragment dintr-un cuvânt evidențiază cuvântul OCR întreg. În PDF digital sunt păstrate casete pe caractere.

## Identități

Ediția este derivată stabil din SHA-256. Pagina și segmentul au ID-uri deterministe sub acea ediție. Sursele se identifică prin identificatorul bibliografic furnizat sau prin metadatele declarate. Indicii canonici au UUID propriu și nu se comasează după ortografie. Aparițiile și intervalele repetate au ID-uri deterministe; reutilizarea unui indice existent cere ID-ul ales explicit.

Un fișier PDF schimbat produce altă ediție. Textul și geometria deja importate sunt imuabile prin trigger-e. Corectarea OCR nu poate rescrie pe ascuns dovezile acceptate; editarea versionată a transcrierii rămâne de dezvoltat.

Relațiile nu sunt duplicate automat după subiect/predicat/obiect. Reutilizarea manuală a unui `relation_id` este permisă numai cu aceeași semnătură, inclusiv conector, negație, modalitate, atribuire și timp verbal. Fiecare dovadă nouă este păstrată distinct în `RelationEvidence`.
