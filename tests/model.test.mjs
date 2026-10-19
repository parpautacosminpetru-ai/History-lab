import test from "node:test";
import assert from "node:assert/strict";
import {historicalToAxis,axisToHistorical,historicalYearLabel,dateAxis,
  uniqueTerms,textKey,findExistingPassage,passageFingerprint,
  queryEntries,matchesPeriod,validateBackup} from "../app/src/main/assets/model.js";

test("cronologia istorică nu introduce anul 0",()=>{
  assert.equal(historicalToAxis(-1),0);
  assert.equal(historicalToAxis(1),1);
  assert.equal(historicalToAxis(0),null);
  assert.equal(axisToHistorical(0),-1);
  assert.equal(historicalYearLabel(-44),"44 î.Hr.");
});
test("termenii se unifică fără a multiplica indexurile",()=>{
  assert.deepEqual(uniqueTerms("Armată; reformă, ARMATA; instituții; reformă"),
    ["Armată","reformă","instituții"]);
  assert.equal(textKey("Știință"),textKey("stiinta"));
});
test("fragmentul canonic respectă sursa, locul și formularea exactă",()=>{
  const p={id:"p1",sourceId:"s1",chapter:"I",pageStart:"41",pageEnd:"42",
    paragraph:"2",sentence:"1",line:"8",quote:"Forma exactă."};
  assert.equal(findExistingPassage([p],{...p,id:"new"})?.id,"p1");
  assert.equal(findExistingPassage([p],{...p,quote:"Altă formă exactă."}),null);
  assert.equal(findExistingPassage([p],{...p,pageStart:"43"}),null);
  assert.notEqual(passageFingerprint(p),passageFingerprint({...p,quote:"Formă exactă."}));
});
const sample={
  sources:[{id:"s1",title:"Lucrarea A",author:"Autor A",speciality:"istorie"},
           {id:"s2",title:"Lucrarea B",author:"Autor B",speciality:"medievistică"}],
  passages:[{id:"p1",sourceId:"s1",chapter:"I",pageStart:"41",quote:"Textul A."},
            {id:"p2",sourceId:"s2",chapter:"IV",pageStart:"110",quote:"Textul B."}],
  entries:[{id:"e1",type:"eveniment",title:"Afirmație în două surse",
    yearStart:1450,yearEnd:null,place:"Locul 1",topics:["economie","instituții"],
    indexes:["termen"],people:"Personaj",paraphrase:"",
    passageIds:["p1","p2"]},
    {id:"e2",type:"periodizare",title:"Încadrare atribuită autorului",
     yearStart:1200,yearEnd:1600,place:"",topics:[],indexes:[],passageIds:["p1"]}],
  relations:[{id:"r1",fromId:"e1",toId:"e2",kind:"Relație exprimată",passageId:"p1"}]
};
test("o fișă e accesibilă din două surse fără copierea textelor",()=>{
  const one=queryEntries(sample,{search:"Lucrarea B"});
  assert.deepEqual(one.map(e=>e.id),["e1"]);
  const two=queryEntries(sample,{sourceId:"s1"});
  assert.equal(two.length,2);
  assert.equal(sample.entries[0].passageIds.length,2);
  assert.equal(sample.passages.length,2);
});
test("căutare din cuvinte și filtre tematice temporale",()=>{
  assert.equal(queryEntries(sample,{search:"institutii 1450"}).length,1);
  assert.equal(queryEntries(sample,{type:"periodizare"}).length,1);
  assert.equal(queryEntries(sample,{timeOnly:true,center:500,span:300}).length,0);
  assert.equal(queryEntries(sample,{timeOnly:true,center:1400,span:500}).length,2);
  assert.equal(matchesPeriod(sample.entries[0],1450,100),true);
  assert.equal(dateAxis(sample.entries[0]),1450);
});
test("importul respinge legăturile către documente absente",()=>{
  const valid={format:"historylab-explicit-1",...structuredClone(sample)};
  assert.doesNotThrow(()=>validateBackup(valid));
  assert.throws(()=>validateBackup({...valid,passages:[]}),/dovadă|sursă/);
  assert.throws(()=>validateBackup({...valid,relations:[{id:"r1",fromId:"e1",toId:"absent",passageId:"p1"}]}),/Relație/);
});
