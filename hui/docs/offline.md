# Offline, pachete și recuperare

Un `.hui` versiunea 1 este un ZIP **stored** (fără compresie sau criptare), cu:

```text
manifest.json
catalog.sqlite
originals/<sha256>.pdf          # opțional
pages/<edition-id>/<page>.png   # opțional, aceeași politică de distribuire
```

Manifestul include `format: "hui"`, `format_version: 1`, `schema_version: 1`, `index_version`, `includes_originals` și un dicționar `files` cu SHA-256 și dimensiune pentru fiecare fișier, exceptând manifestul însuși. Hash-urile detectează coruperea; nu reprezintă o semnătură de autenticitate a editorului.

Exportul fără originale nu conține nici rastere, nici PDF-uri. Cititorul afișează textul indexat și coordonatele, indicând explicit că scanarea necesită originalul corespunzător. Atașarea unui PDF local separat, verificat după hash, rămâne de implementat; în 0.1 se reexportă cu documentele permise.

## Verificări

Importul respinge căi absolute, `..`, segmente goale, căi Windows, intrări duplicate, legături simbolice, fișiere neobișnuite, versiuni incompatibile, fișiere neprevăzute în manifest și diferențe de hash. Reader verifică antetele ZIP înainte de decodare. Schema SQLite trebuie să corespundă exact schemei cunoscute; vizualizările sau trigger-ele suplimentare sunt respinse. Baza este deschisă read-only, cu `trusted_schema=OFF`. Nu se încarcă extensii SQLite.

Limite de siguranță inițiale: Indexer maximum 2 GiB și 50.000 de fișiere per pachet; Reader maximum 256 MiB, deoarece decodarea arhivei este în memorie. Manifestul are maximum 4 MiB. Pentru colecții mai mari trebuie implementat import în flux; nu există o promisiune de suport nelimitat în acest prototip.

## Backup și actualizare

CLI: `python -m hui_indexer.cli --workspace DESTINAȚIE import colectie.hui` verifică într-un director temporar adiacent, mută baza veche într-un backup și instalează directorul nou. Dacă mutarea eșuează, baza anterioară este restaurată. Dacă procesul a fost întrerupt după mutarea bazei vechi, următorul import recuperează backup-ul cunoscut. Backup-urile suplimentare nu sunt șterse automat.

Reader: fiecare import reușit creează un director `index-<id>` separat. `active.json` indică versiunea curentă; `active.backup.json` păstrează pointerul anterior. Fișierele originale ale colecției precedente rămân pe disc. La pornire, lipsa pointerului activ permite folosirea celui de backup. Un import invalid nu schimbă colecția afișată. Nu există încă o interfață de administrare/ștergere a backup-urilor sau de fuziune a două colecții.

Actualizarea în 0.1 înlocuiește atomic instantaneul activ; nu aplică delta-uri și nu comasează indecși independenți. ID-urile păstrate de Indexer rămân aceleași în pachetele următoare.

Nici căutarea, nici navigarea, nici imaginile locale nu necesită internet sau AI. Compilarea și instalarea inițială a dependențelor pot necesita internet. Workflow-ul APK verifică lipsa permisiunilor Android `INTERNET` și `ACCESS_NETWORK_STATE`; testul de integrare utilizează o variantă temporară cu acces loopback pentru comunicarea cu harness-ul Flutter, cu Wi-Fi și datele mobile oprite. Acea variantă nu este distribuită ca artefact.
