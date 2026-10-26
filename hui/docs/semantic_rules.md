# Semantica indexării și căutării

Un indice este o identitate; o apariție este trimiterea exactă spre text. Două forme identice nu primesc automat aceeași identitate. Refolosirea unui ID este o alegere explicită. O traducere devine variantă de căutare numai după înregistrare, justificare și confirmare umană.

Relația păstrează subiectul, obiectul, tipul, conectorul literal, negația, modalitatea, atribuirea și timpul verbal declarat. Pasajul integral rămâne accesibil. Confirmarea umană a unei adnotări nu transformă opinia atribuită într-un fapt istoric certificat.

Validatorul conservator respinge transformarea unor marcatori de negație în relație pozitivă, a unor marcatori condiționali în certitudine și a unei voci atribuite în afirmație fără atribuire. Aceste verificări sunt reguli limitate, nu un parser lingvistic universal: pot cere revizuire suplimentară, pot respinge cazuri valide și nu detectează toate omisiunile. Nu se calculează „100% semantic” din succesul lor.

## Moduri de căutare

| Mod | Ce recuperează |
| --- | --- |
| `text` | Formulări originale, prin FTS5; fără o afirmație despre legătura semantică |
| `index` | Apariții ale identităților canonice sau variantelor validate |
| `linked` | Dovezi ale unei relații explicite ale cărei capete satisfac expresia |

În `linked`, toți termenii unei conjuncții trebuie să se potrivească subiectului/obiectului **aceleiași relații**. Nu se construiește o cale presupusă prin alte capitole sau coapariții. Relațiile negate sunt excluse implicit; includerea lor este explicită și negația rămâne afișată. Modalitatea și atribuirea nu sunt eliminate din rezultat.

## Operatorii

Prioritatea este `NOT`, apoi `AND`/`+`/spațiu, apoi `OR`. Parantezele modifică prioritatea. Ghilimelele ASCII păstrează o expresie ca termen unic. În modul text termenii sunt transformați în expresii FTS literale; nu devin SQL sau comenzi FTS arbitrare.

`AND` cere fiecare criteriu în unitatea aleasă; `OR` cere cel puțin unul; `NOT` exclude unitățile care îndeplinesc criteriul. Pentru căutarea prin indice, termenul trebuie să corespundă **întregii etichete normalizate**, nu unui prefix ghicit.

| Unitate | Delimitare în prototip |
| --- | --- |
| `passage` | Același segment de pagină |
| `context` | Segmente cu același părinte structural, inclusiv structuri propuse |
| `source` | Aceeași lucrare, inclusiv edițiile înregistrate sub acea sursă |

Filtrul cronologic verifică intervalele declarate pe indici care au apariții confirmate în segment. Nu utilizează anul publicării drept data evenimentului. Filtrele pentru autor și tipul relației sunt exacte. Starea implicită semantică este `human_confirmed`; consultarea propunerilor necesită selectarea explicită a stărilor.

Ordinea este reproductibilă: titlu binar, hash-ul ediției, pagină PDF, ordine de lectură și ID. Nu există scor AI, embeddings sau reranking. Paginarea este `limit`/`offset`, maximum 200 de rezultate per cerere.

Parserul de întrebare acceptă forma `Unde apare TERMEN în legătură cu TERMEN?` și o transformă în modul `linked`. Alte întrebări cer alegerea explicită a filtrelor. Un rezultat este întotdeauna o sursă și un pasaj, niciodată un răspuns generat.
