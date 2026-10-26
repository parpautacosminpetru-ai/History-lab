# Import și indexare

## Atelierul local

Pornește `python -m hui_indexer.cli --workspace hui-workspace gui`.

1. **Import PDF** permite selectarea mai multor fișiere, titlul, autorul și limba. Pentru scanări indică limba Tesseract instalată (`ron`, `eng`, `fra`, `deu`, `lat` sau combinații cu `+`). Gol înseamnă că OCR nu este executat.
2. Alege pagina din listă. Textul extras și imaginea originală sunt afișate simultan. Ordinea de lectură rămâne marcată ca incertă până la verificare, mai ales pentru coloane multiple.
3. Selectează în text expresia exactă. Creează un indice sau alege ID-ul unuia existent; **Adnotează selecția** păstrează trimiterea și dreptunghiurile.
4. Pentru o relație, selectează pasajul care cuprinde ambele apariții, apoi alege subiectul și obiectul. Introdu tipul, conectorul exact, modalitatea și atribuirea; declară negația.
5. Lista propunerilor permite revizuire individuală sau în lot, cu numele revizorului. Confirmarea automată a coordonatelor nu confirmă semantica. **Corectează eticheta** se aplică numai unui indice propus. O apariție/relație greșită se respinge și se creează o propunere corectată, păstrând istoricul.
6. **Structură** corectează titlul și intervalul unei structuri existente. **Pagină tipărită** păstrează eticheta exactă, inclusiv cifre romane. **Transcriere verificată** se bifează numai după confruntarea completă cu imaginea.
7. **Publică + exportă** validează și exportă instantaneul; includerea PDF-urilor cere declararea dreptului de distribuire.

Operațiile de extragere ale atelierului sunt sincrone în acest prototip; fereastra poate rămâne ocupată pe durata OCR. CLI este potrivit pentru loturi mari. Interfața nu ascunde acest cost prin rezultate simulate.

## CLI pentru adnotări

`list segments`, `list nodes`, `list structures`, `list pending`, `list occurrences --node-id ID` expun identificatorii și coordonatele. Fiecare listă are maximum 200 de înregistrări și acceptă `--offset`.

```sh
python -m hui_indexer.cli --workspace hui-workspace node domnie --type concept --language ro
python -m hui_indexer.cli --workspace hui-workspace annotate aparitie.json
python -m hui_indexer.cli --workspace hui-workspace relation relatie.json
python -m hui_indexer.cli --workspace hui-workspace review decizii.json --reviewer "Numele revizorului"
python -m hui_indexer.cli --workspace hui-workspace provenance ID_APARITIE
```

`aparitie.json` conține chei `node_id`, `parts` (listă de `{segment_id,start,end}`), opțional `quote`, `language`, `uncertainty`. `quote`, dacă este furnizat, trebuie să coincidă exact cu intervalul sursei. Pentru mai multe părți, reprezentarea textuală le unește cu un separator `\n`; sursa și fiecare poziție rămân distincte.

`relatie.json` conține `subject_occurrence_id`, `object_occurrence_id`, `predicate`, `parts`, `connector`, `negated` boolean, `modality`, `attribution`, opțional `tense`, `uncertainty` și un `relation_id` existent pentru o dovadă suplimentară verificată explicit.

`decizii.json` este o listă de `{type,id,status}`. Tipurile acceptate sunt `node`, `occurrence`, `relation`, `span`, `variant`; stările umane sunt `human_confirmed`, `rejected`, `needs_review`. Pentru a regăsi semantic o apariție în modul implicit trebuie confirmate atât indicele, cât și apariția.

## AI opțional

```sh
python -m hui_indexer.cli --workspace hui-workspace propose ID_SEGMENT --endpoint http://127.0.0.1:11434/v1/chat/completions --model NUME_MODEL --allow-ai
```

Adaptorul local cere adresă numerică loopback și nu folosește proxy-uri. Pentru un API extern sunt necesare `--external --allow-external --allow-ai`, HTTPS și variabila de mediu `HUI_API_KEY`. Textele nu se trimit în lipsa acestor opțiuni. Niciun furnizor real nu este necesar testelor; adaptorul determinist este etichetat pentru teste.

Răspunsul modelului poate crea exclusiv propuneri noi. Etichetele trebuie să fie expresii literale din dovadă; coordonatele, citatul și capetele relațiilor sunt validate într-o singură tranzacție. Instrucțiunile găsite în document nu devin comenzi, căi, endpoint-uri sau instrucțiuni executabile ale Indexer-ului. Nu există unelte pe care modelul să le poată apela.

## Reluare

Importă din nou același PDF după întrerupere. Paginile deja comise sunt păstrate, cele rămase sunt procesate. Hash-ul identic nu produce altă ediție. Adăugarea unei lucrări nu reindexează lucrările existente. Paginile fără text, OCR-ul neconfruntat și ordinea incertă sunt raportate separat în `Issues`.
