import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {validateBackup,passageFingerprint,queryEntries} from "../app/src/main/assets/model.js";

const page = {id:"pg1",sourceId:"s1",pageNumber:"52",chapter:"III",
  imageUrl:"https://appassets.androidplatform.net/pages/original.jpg",
  ocrText:"Conținutul paginii transcris manual după OCR",verified:true};

const archive = {
  format:"historylab-explicit-1",
  sources:[{id:"s1",title:"Sursă de test",author:"Autor"}],
  pages:[page],
  passages:[{id:"p1",sourceId:"s1",pageId:"pg1",pageStart:"52",chapter:"III",
    quote:"Text selectat exact",offsetStart:6,offsetEnd:24}],
  entries:[{id:"e1",passageIds:["p1"],title:"Etichetă manuală",type:"afirmatie",
    topics:["temă"],indexes:["index"],yearStart:null}],
  relations:[]
};

test("fotografia unei surse este păstrată o singură dată",()=>{
  const result=validateBackup(structuredClone(archive));
  assert.equal(result.pages.length,1);
  assert.equal(result.entries.length,1);
  assert.equal(result.passages[0].pageId,result.pages[0].id);
});
test("backup vechi importabil fără pierdere",()=>{
  const older=structuredClone(archive);delete older.pages;
  older.passages[0].pageId=undefined;
  assert.deepEqual(validateBackup(older).pages,[]);
});
test("citatele nu pot trimite la imagini absente",()=>{
  const broken=structuredClone(archive);
  broken.passages[0].pageId="missing-page";
  assert.throws(()=>validateBackup(broken),/fotografie absentă/);
});
test("nu afișa în căutare toate fișele de pe o pagină din cauza unui cuvânt OCR neindexat",()=>{
  const one=structuredClone(archive);
  one.pages[0].ocrText="În altă parte a aceleiași pagini există cuvântul flotilă";
  const results=queryEntries(one,{search:"flotilă"});
  assert.equal(results.length,0);
});
test("diferența dintre două selecții exacte de citat nu se pierde",()=>{
  assert.notEqual(passageFingerprint({...archive.passages[0],quote:"Text selectat"}),
    passageFingerprint({...archive.passages[0],quote:"Text selectat "}));
});
test("toate controalele atelierului OCR există în interfață",()=>{
  const html=readFileSync(new URL("../app/src/main/assets/index.html",import.meta.url),"utf8");
  const js=readFileSync(new URL("../app/src/main/assets/reader.js",import.meta.url),"utf8");
  const ids=[...js.matchAll(/\$\("([A-Za-z0-9-]+)"\)/g)].map(x=>x[1]);
  for(const id of ids)assert.ok(html.includes('id="'+id+'"'),"Lipsește elementul "+id);
});
