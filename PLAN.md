# HistoryLab – dezvoltare cu istoricul la centru

## Obiectiv

Un mediu de cercetare istorică personal, offline, în care niciun rezultat intelectual nu este produs în locul istoricului. Tehnologia accelerează operațiile repetitive (arhivare, OCR, căutare literală, intersecția criteriilor, citare tehnică), păstrând integral sursele și traseul de verificare.

### Faza 1 – v0.1 (prototip inițial)

- [x] Depozitare locală, imagini originale și amprente SHA-256.
- [x] OCR local cu modele română și engleză incluse la build.
- [x] Separare original / OCR / transcriere corectată / marginalii / sinteză.
- [x] Reguli literale create de istoric și intersecții între axe.
- [x] Localizare de cuvinte pe fotografie prin coordonate OCR și zoom.
- [x] Jurnal al modificărilor de metadate, transcrieri și fișe.
- [x] Export de backup și fișă text.
- [ ] **APK compilat în GitHub Actions și testat efectiv pe telefon.**

### Faza 2 – integritatea cercetării

- [ ] Editor de adnotări cu selecție precisă a cuvintelor/regiunilor, cu offset-uri și coordonate.
- [ ] Document multipagină, relații între documente și identificatori bibliografici stabili.
- [ ] Restaurare ZIP, verificarea hash-urilor și export de arhive interoperabile.
- [ ] Jurnal imuabil cu revizii și operații complete de tip undo.
- [ ] Modificări ale regulilor versionate, evitarea suprascrierilor neintenționate.
- [ ] Citare completă Chicago (note și bibliografie), șabloane multiple validate.
- [ ] Testare OCR pe documente de arhivă, inclusiv fotografii neuniforme.

### Faza 3 – atelier academic extins

- [ ] Import/export PDF, TEI-XML, CSV, RIS și BibTeX.
- [ ] Filtre între axele Localitate, Persoană, Perioadă, Instituție etc. numai după criterii controlate.
- [ ] Vizualizări interactive: hărți, grafuri și cronologii construite din date aprobate de istoric.
- [ ] Organizare proiecte de licență, disertație, teză, monografie, carte.
- [ ] Export DOCX/PDF cu aparat critic și note validate de utilizator.
- [ ] Extensii OCR pentru paleografie și alfabete istorice; suport explicit al incertitudinii.

### Criteriu de acceptare pentru fiecare funcție nouă

Funcția nu inventează informație, nu rescrie originalul, nu ascunde incertitudinile, arată de unde provin datele și oferă istoricului controlul final. Rezultatele indexării automate trebuie să poată fi reproduse pornind de la regula declarată.
