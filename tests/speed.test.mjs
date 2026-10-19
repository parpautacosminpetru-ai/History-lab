import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {candidateSegments,coverageReport,nextCandidate,indexPalette,appendChosenTag} from "../app/src/main/assets/speed.js";
import {passageFingerprint,findExistingPassage} from "../app/src/main/assets/model.js";

test("segmentarea e mecanică și păstrează exact ordinea și ortografia",()=>{
  const t="Prima afirmație. A doua afirmă o reformă!\n\nAlta continuă?";
  const xs=candidateSegments(t);
  assert.deepEqual(xs.map(s=>s.quote),["Prima afirmație.","A doua afirmă o reformă!","Alta continuă?"]);
  for(const s of xs)assert.equal(t.slice(s.start,s.end),s.quote);
  assert.equal(xs[0].start,0);
});

test("delimitarea de sintagme rămâne posibilă fără completări implicite",()=>{
  const t="Reformă militară. Reorganizare civilă.";
  const quote="militară";
  const start=t.indexOf(quote);
  const p={pageId:"pg1",quote,offsetStart:start,offsetEnd:start+quote.length};
  const coverage=coverageReport(t,[p],"pg1");
  assert.ok(coverage.percent>0&&coverage.percent<100);
  assert.equal(coverage.candidates[0].complete,false);
  assert.equal(coverage.candidates[1].complete,false);
});

test("repetarea aceluiași interval nu crește artificial procentul",()=>{
  const t="Un text. Un alt text.";
  const first={pageId:"pg1",quote:"Un text.",offsetStart:0,offsetEnd:8};
  assert.deepEqual(
    coverageReport(t,[first],"pg1").indexed,
    coverageReport(t,[first,first],"pg1").indexed
  );
});

test("editarea OCR nu declară acoperire pentru citate devenite inexacte",()=>{
  const t="Textul exact a fost indexat.";
  const p={pageId:"pg",quote:t,offsetStart:0,offsetEnd:t.length};
  assert.equal(coverageReport(t,[p],"pg").percent,100);
  const report=coverageReport("Textul schimbat a fost indexat.",[p],"pg");
  assert.equal(report.indexed,0);
  assert.equal(report.stale,1);
});

test("navigatorul revine circular la următorul segment neacoperit",()=>{
  const t="A. B. C.";
  const segs=candidateSegments(t);
  const p={pageId:"pg",quote:segs[1].quote,offsetStart:segs[1].start,offsetEnd:segs[1].end};
  const progress=coverageReport(t,[p],"pg");
  assert.equal(nextCandidate(progress,0,1,true).quote,"C.");
  assert.equal(nextCandidate(progress,2,1,true).quote,"A.");
  assert.equal(nextCandidate(progress,2,-1,true).quote,"A.");
});

test("paleta nu inventează indici, ci citește exclusiv opțiunile istoricului",()=>{
  const xs=[
    {updatedAt:"2026-10-01",topics:["armată"],indexes:["armată","reformă"]},
    {updatedAt:"2026-09-01",topics:["administrație"],indexes:["reformă"]}
  ];
  assert.deepEqual(indexPalette(xs).map(x=>x.kind+":"+x.name),
    ["index:reformă","topic:armată","index:armată","topic:administrație"]);
  assert.equal(appendChosenTag("armată; Reformă","reformă"),"armată, Reformă");
  assert.equal(appendChosenTag("armată","administrație"),"armată, administrație");
});

test("același citat la două poziții rămâne două ocurențe, nu un fals duplicat",()=>{
  const a={sourceId:"s1",chapter:"III",pageStart:"8",pageId:"pg",quote:"Reformă.",
    offsetStart:1,offsetEnd:9};
  const b={...a,offsetStart:34,offsetEnd:42};
  assert.notEqual(passageFingerprint(a),passageFingerprint(b));
  assert.equal(findExistingPassage([{...a,id:"p1"}],b),null);
  assert.equal(findExistingPassage([{...a,id:"p1"}],a)?.id,"p1");
});

test("controalele de navigare și paletă există în HTML",()=>{
  const html=readFileSync(new URL("../app/src/main/assets/index.html",import.meta.url),"utf8");
  for(const id of ["readerSegmentPrev","readerSegmentNext","readerNextUncovered",
    "readerCoverageBar","readerCoverageLabel","readerPalette","readerUseLastIndices","readerAutoNext"]){
    assert.ok(html.includes('id="'+id+'"'),"Lipsește "+id);
  }
});
