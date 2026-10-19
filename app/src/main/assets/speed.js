/**
 * HistoryLab / Motor de viteză documentară.
 * Segmentele sunt propuneri MECANICE bazate pe punctuație, nu enunțuri
 * verificate semantic. Niciun indice nu este atribuit automat.
 */

export function candidateSegments(text = "") {
  const content = String(text);
  const result = [];
  let start = 0;
  const push = end => {
    if (end <= start) return;
    let a = start, b = end;
    while (a < b && /\s/.test(content[a])) a++;
    while (b > a && /\s/.test(content[b - 1])) b--;
    if (b > a) result.push({start: a, end: b, quote: content.slice(a, b)});
    start = end;
  };
  for (let i = 0; i < content.length; i++) {
    const char = content[i], next = content[i + 1];
    if ((char === "." || char === "?" || char === "!" || char === ";" || char === "…") &&
       (next === undefined || /\s/.test(next))) {
      push(i + 1);
    } else if (char === "\n" && content[i + 1] === "\n") {
      push(i + 1);
    }
  }
  push(content.length);
  return result;
}

export function verifiedSpans(text = "", passages = [], pageId = "") {
  const content = String(text);
  const valid = [];
  let stale = 0, unknown = 0;
  for (const p of passages) {
    if (pageId && p.pageId !== pageId) continue;
    if (!Number.isInteger(p.offsetStart) || !Number.isInteger(p.offsetEnd)) {
      unknown++; continue;
    }
    if (p.offsetStart < 0 || p.offsetEnd <= p.offsetStart || p.offsetEnd > content.length
       || content.slice(p.offsetStart, p.offsetEnd) !== p.quote) {
      stale++; continue;
    }
    valid.push({start: p.offsetStart, end: p.offsetEnd});
  }
  return {valid, stale, unknown};
}

export function coverageReport(text = "", passages = [], pageId = "") {
  const content = String(text), {valid, stale, unknown} = verifiedSpans(content,passages,pageId);
  // Acoperire a caracterelor non-spațiu. Nu măsoară exhaustivitatea semantică!
  const coverage = new Uint8Array(content.length);
  for (const {start,end} of valid) coverage.fill(1,start,end);
  let total = 0, indexed = 0;
  for (let i = 0; i < content.length; i++) {
    if (/\s/.test(content[i])) continue;
    total++;
    if (coverage[i]) indexed++;
  }
  const candidates = candidateSegments(content).map((segment,i)=>{
    let significant = 0, counted = 0;
    for(let j=segment.start;j<segment.end;j++){
      if(/\s/.test(content[j]))continue;
      significant++;
      if(coverage[j]) counted++;
    }
    return {...segment,index:i,complete:significant>0&&counted===significant,
      covered:counted,total:significant};
  });
  return {total,indexed,percent:total ? Math.round(100*indexed/total) : 0,
    stale,unknown,candidates};
}

export function nextCandidate(report, after = -1, direction = 1, preferUncovered = false) {
  const candidates = report?.candidates || [];
  if(!candidates.length)return null;
  // Începe STRICT după poziția curentă; la capăt reia de la început.
  const n=candidates.length;
  let cursor=direction<0
    ? (after<0?n:after)
    : (after<0?-1:after);
  for(let count=0;count<n;count++){
    cursor=(cursor+(direction<0?-1:1)+n)%n;
    const candidate=candidates[cursor];
    if(!preferUncovered || !candidate.complete)return candidate;
  }
  return null;
}

export function indexPalette(entries = [], limit = 18, maxScan = 1200) {
  const ranks = new Map();
  const recent = entries.slice().sort((a,b)=>
    String(b.updatedAt||b.createdAt||"").localeCompare(String(a.updatedAt||a.createdAt||""))).slice(0,maxScan);
  recent.forEach((entry,i)=>{
    const categories = [["topic",entry.topics||[]],["index",entry.indexes||[]]];
    categories.forEach(([kind,labels])=>{
      labels.forEach(value=>{
        const name=String(value).trim();if(!name)return;
        const key=kind+"|"+name.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
        const old=ranks.get(key);
        if(old){old.count++;return;}
        ranks.set(key,{kind,name,key,count:1,last:i});
      });
    });
  });
  return [...ranks.values()].sort((a,b)=>a.last-b.last||b.count-a.count)
    .slice(0,limit).map(({kind,name})=>({kind,name}));
}

export function appendChosenTag(existing = "", item = "") {
  const terms=String(existing).split(/[,;\n]+/).map(s=>s.trim()).filter(Boolean);
  const name=String(item).trim();
  if(!name)return terms.join(", ");
  const key=s=>s.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
  if(!terms.some(term=>key(term)===key(name)))terms.push(name);
  return terms.join(", ");
}
