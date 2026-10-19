import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {performance} from 'node:perf_hooks';
import {queryEntries,entrySearchText,validateBackup} from '../app/src/main/assets/model.js';

const makeData=n=>({
  sources:[{id:'s',title:'Lucrare de referință',author:'Autor'}],
  passages:Array.from({length:n},(_,i)=>({id:'p'+i,sourceId:'s',quote:'Reforma militară din document '+i,pageStart:String(1+(i/2|0))})),
  entries:Array.from({length:n},(_,i)=>({id:'e'+i,passageIds:['p'+i],title:'Reforma '+i,type:'afirmatie',topics:['armată'],indexes:['reformă'],yearStart:null})),
  relations:[],pages:[]
});

test('sursa se regăsește prin toate fișele fără duplicarea pasajelor',()=>{
 const d=makeData(1000);
 assert.equal(queryEntries(d,{search:'militară'}).length,1000);
 assert.equal(queryEntries(d,{search:'autor'}).length,1000);
 assert.equal(queryEntries(d,{sourceId:'s'}).length,1000);
 assert.equal(d.passages.length,1000);
});

test('filtrarea timpului este opțională, nu ascunde implicit fișe nedatate',()=>{
 const d=makeData(2);
 assert.equal(queryEntries(d,{}).length,2);
 assert.equal(queryEntries(d,{timeOnly:true,center:1800,span:200}).length,0);
 const html=readFileSync(new URL('../app/src/main/assets/index.html',import.meta.url),'utf8');
 assert.match(html,/id="timeOnly" type="checkbox"/);
 assert.doesNotMatch(html,/id="timeOnly" type="checkbox" checked/);
});

test('indexurile se reîmprospătează la încărcarea unui nou instantaneu',()=>{
 const d=makeData(1);
 assert.equal(queryEntries(d,{search:'militară'}).length,1);
 assert.equal(queryEntries(d,{search:'reformă'}).length,1);
 const updated=structuredClone(d);
 updated.passages[0].quote='Expediție maritimă';
 updated.entries[0].title='Călătorie';updated.entries[0].topics=[];updated.entries[0].indexes=[];
 assert.equal(queryEntries(updated,{search:'militară'}).length,0);
 assert.equal(queryEntries(updated,{search:'maritimă'}).length,1);
});

test('ordinea originală a paginilor păstrează ordinea numerică',()=>{
 const d=makeData(2);d.passages[0].pageStart='10';d.passages[1].pageStart='2';
 assert.deepEqual(queryEntries(d,{sort:'source'}).map(e=>e.id),['e1','e0']);
});

test('același indice cu diacritice este căutabil fără pierdere',()=>{
 const d=makeData(1);
 assert.equal(queryEntries(d,{search:'armata'}).length,1);
 assert.equal(queryEntries(d,{search:'armată'}).length,1);
 assert.equal(queryEntries(d,{search:'militară'}).length,1);
 assert.equal(entrySearchText(d.entries[0],d).includes('reforma'),true);
});

test('căutarea în 5.000 de fișe nu dublează înregistrările',()=>{
 const d=makeData(5000),t=performance.now();
 const results=queryEntries(d,{search:'militară'});
 const first=performance.now()-t;
 assert.equal(results.length,5000);
 assert.equal(new Set(results.map(x=>x.id)).size,5000);
 const t2=performance.now();const cached=queryEntries(d,{search:'reformă'});
 const repeat=performance.now()-t2;
 assert.equal(cached.length,5000);
 console.log("Index snapshot: "+Math.round(first)+"ms first query, "+Math.round(repeat)+"ms subsequent (informational)");
});

test('backup fără sursă sau citat nu poate fi restaurat',()=>{
 const d=makeData(2);
 const bad={...d,format:'historylab-explicit-1',sources:[]};
 assert.throws(()=>validateBackup(bad),/sursă/);
});
