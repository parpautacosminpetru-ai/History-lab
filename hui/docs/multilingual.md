# Limbi și Unicode

Textul PDF/OCR este păstrat în Unicode, fără traducere sau înlocuire cu rezumat. Prioritatea de configurare OCR este: română `ron`, engleză `eng`, franceză `fra`, germană `deu`, latină `lat`. Pachetele Tesseract trebuie instalate separat; disponibilitatea lor se verifică prin `tesseract --list-langs`. Nu există descărcare automată de modele la import.

Limba este declarată de utilizator. Dacă lipsește, se păstrează `und` și se creează o problemă pentru revizuire. Detectarea automată fiabilă a limbilor și paginilor multilingve nu este implementată în 0.1. OCR poate primi combinații precum `ron+fra`; textul rezultat rămâne o transcriere neconfirmată.

Forma normalizată de căutare folosește un tabel Unicode versionat, generat prin case folding, NFKD și eliminarea caracterelor cu clasă de combinare nenulă. Același tabel este livrat Python și Flutter; nu depinde de locale-ul Windows/Android. FTS5 utilizează propriul tokenizer `unicode61 remove_diacritics 2`; acesta nu echivalează cu lematizare, traducere sau segmentare lingvistică pentru orice scriere.

`NodeVariants` separă forma, limba și dovada justificativă. O variantă propusă nu extinde căutarea semantică până la confirmarea umană. Termenii fără corespondență validată rămân distincți. Textul original poate fi căutat textual chiar dacă nu există încă un indice echivalent; acest rezultat nu certifică identitatea conceptuală.

Testele includ documente originale românești, franceze și germane, OCR englezesc, diacritice, `ß`, un caracter suplimentar Unicode și echivalențe validate/nevalidate. Limba latină are suport de stocare și configurare OCR, dar nu este încă testată cu un corpus latin real.
