# Limitări și sarcini de continuare

HUI 0.1 este un prototip verificabil, nu implementarea integrală a tuturor fazelor specificației.

| Componentă | Ce există | Ce rămâne |
| --- | --- | --- |
| PDF/OCR | Text, casete, rastere, rotații, CropBox, OCR local, reluare pe pagini | Ordine verificată pentru coloane multiple, recuperare tipografică și despărțiri, segmentare robustă pe paragrafe/propoziții |
| Structură | Document și capitole propuse prin titluri explicite; corectarea titlului/intervalului; pagini tipărite manual | Cuprins, ierarhii complexe, realocarea segmentelor după schimbarea limitelor capitolului, editor structural complet |
| Fidelitate | Original nemodificat, hash, text imuabil, ancore și audit | Revizii OCR corectate, versionate și realiniate fără ruperea ancorelor existente |
| Semantica | Identități alese explicit, apariții, intervale multipagină/suprapuse, relații și modificatori, variante validate | Parser lingvistic riguros multilingv, politici de dezambiguizare asistată, validarea semantică sistematică pe corpus |
| AI | Adaptor local/API extern cu acord explicit, adaptor determinist, validare tranzacțională | Evaluare cu furnizori reali și corpus de referință; nu există o măsură de exhaustivitate AI |
| Căutare | AND/OR/NOT, domenii distincte, filtre, FTS5, relații, întrebare limitată, ordine reproductibilă | Gramatică mai bogată, traversări de mai multe relații cu semantică explicită, paginare prin cursor pentru colecții mari |
| Afirmații recurente | Dovezi multiple atașate explicit unei relații cu semnătură identică | Grupare revizuită a formulărilor diferite, editor/comparator dedicat |
| Reader | Bibliotecă, filtre, context, raster/PDF, evidențiere, traseu bidirecțional, acoperire | Testare UX cu istorici și accesibilitate completă; atelierul editabil este separat, în Tk |
| Coordonate | Tabel rar pentru perechi de tipuri de indici legate explicit | Axe sursă/cronologie extinse, incluziuni și stratificări, filtrare la nivelul unei celule; nu există hartă istorică generată |
| Pachete | Export/import, hash-uri, backup, înlocuire atomică, index fără PDF | Import/export streaming, delta-uri, fuziune controlată, administrarea backup-urilor, semnături de autenticitate |
| Platforme | Implementare Windows/Android și workflows; rezultate în raport | Teste pe telefoane fizice, sesiuni lungi, semnare de producție, instalatoare și actualizări |
| Migrare | Schema 1, inițializare tranzacțională, respingerea versiunilor necunoscute | Migrare către schema următoare și conversia separată a datelor HistoryLab |

Atelierul Tk procesează importul/OCR sincron; pentru loturi mari utilizează CLI. Casetele digitale pe caractere cresc dimensiunea SQLite. Toate paginile sunt marcate inițial cu ordine de lectură de verificat. OCR este o transcriere, nu text original garantat, iar confirmarea transcrierii nu certifică toate adnotările semantice.

Niciun procent de pagini procesate nu se prezintă drept exhaustivitate semantică. Absența rezultatelor într-un index incomplet nu dovedește absența informației în sursă.

## Sarcini independente pentru următoarea iterație

1. Structuri și OCR: adnotări de paragraf/propoziție, editor versionat și realiniere, corpus cu coloane multiple și scanări degradate.
2. Semantica explicită: benchmark multilingv de negație/modalitate/atribuire, validare umană comparată și furnizori reali opționali.
3. Reader și atelier: editor de validare Windows mai complet, comparație între dovezi, criterii matriceale și accesibilitate.
4. Pachete și scară: streaming, limite măsurate pe dispozitive Android, delta-uri și politici de backup/migrare.
5. Distribuție: verificare pe dispozitive fizice, semnare stabilă, instalator și auditul dependențelor înainte de producție.
