import {newId, textKey, uniqueTerms, historicalToAxis, axisToHistorical,
  historicalYearLabel, dateLabel, dateAxis, matchesPeriod, findExistingPassage,
  queryEntries, loadData, putObjects, removeObject, replaceData, makeBackup} from "./model.js";

const $ = id => document.getElementById(id);
const types = {eveniment:"EVENIMENT",afirmatie:"AFIRMAȚIE",persoana:"PERSOANĂ",teritoriu:"TERITORIU",
  institutie:"INSTITUȚIE",periodizare:"PERIODIZARE"};
const empty = () => ({sources:[], passages:[], entries:[], relations:[]});
const esc = s => String(s ?? "").replace(/[&<>"']/g, c =>
  ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const htmlLines = s => esc(s).replace(/\n/g, "<br>");
const clamp = (v,min,max) => Math.min(max,Math.max(min,v));
const numberOrNull = s => s === "" || s === null || s === undefined ? null : Number(s);
const sourceOf = id => data.sources.find(s => s.id === id);
const passageOf = id => data.passages.find(p => p.id === id);
const entryOf = id => data.entries.find(e => e.id === id);

let data=empty(), world=null, tab="entries", selectedId=null, selectedSource=null;
let currentSourceId=null, currentEntryId=null, mode=null, draftPolygon=[];
let toastTimer, renderedDots=[], renderedTime=[];
let timeline={center:500, span:5000}, map={lon:19, lat:46, zoom:2.2};
let timeDrag=null, mapPointers=new Map(), mapLast=null, mapWasDragged=false;

const scene = $("mapCanvas"), ruler = $("timeCanvas");
const sceneCtx = scene.getContext("2d"), timeCtx = ruler.getContext("2d");
let sceneW=0, sceneH=0, rulerW=0, rulerH=0, scheduled=false;

function notice(message) {
  clearTimeout(toastTimer);
  $("toast").textContent=message;
  $("toast").classList.add("show");
  toastTimer=setTimeout(()=>$("toast").classList.remove("show"),3400);
}
function closeMenu(){ $("actionMenu").classList.add("hidden"); }
function resizeCanvas(canvas) {
  const r=canvas.getBoundingClientRect(), dpr=Math.min(2,window.devicePixelRatio||1);
  if (canvas.width!==Math.round(r.width*dpr) || canvas.height!==Math.round(r.height*dpr)) {
    canvas.width=Math.round(r.width*dpr);canvas.height=Math.round(r.height*dpr);
  }
  const ctx=canvas.getContext("2d");
  ctx.setTransform(dpr,0,0,dpr,0,0);
  return [r.width,r.height];
}
function resize() {
  [sceneW,sceneH]=resizeCanvas(scene);
  [rulerW,rulerH]=resizeCanvas(ruler);
  draw();
}
function scheduleDraw() {
  if(scheduled)return;
  scheduled=true; requestAnimationFrame(()=>{scheduled=false;draw();});
}
function mapScale(){return Math.min(sceneW/360,sceneH/180)*map.zoom;}
function coordToScreen(lon,lat){
  const s=mapScale();
  return {x:sceneW/2+(lon-map.lon)*s,y:sceneH/2+(map.lat-lat)*s};
}
function screenToCoord(x,y){
  const s=mapScale();
  return {lon:clamp(map.lon+(x-sceneW/2)/s,-180,180),lat:clamp(map.lat-(y-sceneH/2)/s,-90,90)};
}
function zoomMap(factor,x=sceneW/2,y=sceneH/2) {
  const anchor=screenToCoord(x,y);
  map.zoom=clamp(map.zoom*factor,.73,70);
  const next=screenToCoord(x,y);
  map.lon=clamp(map.lon+(anchor.lon-next.lon),-180,180);
  map.lat=clamp(map.lat+(anchor.lat-next.lat),-85,85);
  scheduleDraw();
}
function drawWorld(ctx) {
  if (!world?.features?.length) return;
  ctx.lineWidth=.6;ctx.strokeStyle="#9db8aa";ctx.fillStyle="#d7e3d8";
  const drawRing=points=>{
    if(!points?.length) return;
    let prev=null;
    for(const pair of points){
      const pt=coordToScreen(pair[0],pair[1]);
      if(!prev||Math.abs(pair[0]-prev[0])>180)ctx.moveTo(pt.x,pt.y);
      else ctx.lineTo(pt.x,pt.y);
      prev=pair;
    }
    ctx.closePath();
  };
  for(const feat of world.features){
    const g=feat.geometry;
    if(!g)continue;
    const polys=g.type==="Polygon"?[g.coordinates]:(g.type==="MultiPolygon"?g.coordinates:[]);
    for(const poly of polys){
      ctx.beginPath();
      for(const ring of poly) drawRing(ring);
      ctx.fill("evenodd");
      ctx.stroke();
    }
  }
}
function drawGrid(ctx) {
  const s=mapScale();
  let step=s>8?5:s>3?10:30;
  ctx.lineWidth=.6;ctx.strokeStyle="#d2e2df";
  ctx.font="10px system-ui";ctx.fillStyle="#93a9a4";
  for(let lon=-180;lon<=180;lon+=step){
    const a=coordToScreen(lon,-90),b=coordToScreen(lon,90);
    if(a.x<0||a.x>sceneW)continue;
    ctx.beginPath();ctx.moveTo(a.x,0);ctx.lineTo(a.x,sceneH);ctx.stroke();
    if(a.x>8&&a.x<sceneW-45)ctx.fillText(lon===0?"0°":Math.abs(lon)+"°"+(lon<0?"V":"E"),a.x+3,sceneH-8);
  }
  for(let lat=-90;lat<=90;lat+=step){
    const p=coordToScreen(0,lat);
    if(p.y<0||p.y>sceneH)continue;
    ctx.beginPath();ctx.moveTo(0,p.y);ctx.lineTo(sceneW,p.y);ctx.stroke();
    if(p.y>12&&p.y<sceneH-5)ctx.fillText(lat===0?"Ecuator":Math.abs(lat)+"°"+(lat<0?"S":"N"),sceneW-47,p.y-3);
  }
}
function parseGeometry(value) {
  if(!value||!value.trim())return [];
  const pts=value.split(/[;\n]+/).filter(x=>x.trim()).map(segment=>{
    const parts=segment.trim().split(/[,\s]+/).map(Number);
    if(parts.length!==2 || parts.some(n=>!Number.isFinite(n)))throw new Error("Conturul trebuie să conțină perechi longitudine,latitudine.");
    if(Math.abs(parts[0])>180||Math.abs(parts[1])>90)throw new Error("Coordonate geografice în afara limitelor.");
    return parts;
  });
  if(pts.length>0&&pts.length<3)throw new Error("Un contur are nevoie de minimum trei puncte.");
  return pts;
}
function drawTerritory(ctx,entry,dim=false) {
  const pts=entry.geometry||[];
  if(pts.length<3)return;
  ctx.beginPath();
  pts.forEach((p,i)=>{
    const v=coordToScreen(p[0],p[1]);
    if(i===0)ctx.moveTo(v.x,v.y);else ctx.lineTo(v.x,v.y);
  });
  ctx.closePath();
  ctx.fillStyle=entry.id===selectedId?"rgba(185,135,64,.30)":"rgba(41,114,99,.15)";
  ctx.strokeStyle=entry.id===selectedId?"#b08343":"#397a69";
  ctx.lineWidth=entry.id===selectedId?2.5:1.35;
  ctx.fill();ctx.stroke();
}
function showableEntries() {
  return queryEntries(data,queryOptions()).filter(e=>!$("timeOnly").checked
    || matchesPeriod(e,timeline.center,timeline.span,false));
}
function drawScene() {
  if(!sceneW||!sceneH)return;
  const ctx=sceneCtx;
  ctx.clearRect(0,0,sceneW,sceneH);
  ctx.fillStyle="#e8f2f1";ctx.fillRect(0,0,sceneW,sceneH);
  drawGrid(ctx);drawWorld(ctx);
  const visible=showableEntries(),visibleIds=new Set(visible.map(e=>e.id));
  for(const e of visible)drawTerritory(ctx,e);

  // Legăturile vizibile sunt exclusiv cele adăugate explicit, cu dovadă textuală.
  ctx.save();ctx.strokeStyle="#a77b4b";ctx.lineWidth=1.6;ctx.setLineDash([5,4]);
  for(const r of data.relations){
    if(!visibleIds.has(r.fromId)||!visibleIds.has(r.toId))continue;
    const a=entryOf(r.fromId),b=entryOf(r.toId);
    if(a?.lat==null||a?.lon==null||b?.lat==null||b?.lon==null)continue;
    const p=coordToScreen(a.lon,a.lat),q=coordToScreen(b.lon,b.lat);
    ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.stroke();
  }
  ctx.restore();

  // Suprapuneri controlate: punctele apropiate devin un grup selectabil.
  const groups=[];
  for(const entry of visible){
    if(entry.lat==null||entry.lon==null)continue;
    const p=coordToScreen(entry.lon,entry.lat);
    if(p.x< -35||p.x>sceneW+35||p.y< -35||p.y>sceneH+35)continue;
    let g=groups.find(g=>Math.hypot(g.x-p.x,g.y-p.y)<20);
    if(g)g.items.push(entry);
    else groups.push({x:p.x,y:p.y,items:[entry]});
  }
  renderedDots=groups;
  for(const group of groups){
    const sel=group.items.some(e=>e.id===selectedId);
    const rad=sel?11:group.items.length>1?10:7.2;
    ctx.beginPath();ctx.arc(group.x,group.y,rad+2.5,0,Math.PI*2);
    ctx.fillStyle="#fdfef9";ctx.fill();
    ctx.beginPath();ctx.arc(group.x,group.y,rad,0,Math.PI*2);
    ctx.fillStyle=sel?"#b28649":"#24766c";ctx.fill();
    if(group.items.length>1){
      ctx.fillStyle="#fff";ctx.textAlign="center";ctx.textBaseline="middle";
      ctx.font="bold 10px system-ui";ctx.fillText(String(group.items.length),group.x,group.y+0.5);
    }else if(map.zoom>4||sel){
      const e=group.items[0];
      ctx.fillStyle="rgba(254,255,251,.92)";
      ctx.textAlign="left";ctx.textBaseline="middle";ctx.font="600 11px system-ui";
      const label=e.title.slice(0,36),wid=ctx.measureText(label).width;
      ctx.fillRect(group.x+rad+5,group.y-10,wid+10,20);
      ctx.fillStyle="#294b45";ctx.fillText(label,group.x+rad+10,group.y);
    }
  }
  if(draftPolygon.length){
    ctx.beginPath();
    draftPolygon.forEach((p,i)=>{const s=coordToScreen(p[0],p[1]);if(i===0)ctx.moveTo(s.x,s.y);else ctx.lineTo(s.x,s.y);});
    ctx.strokeStyle="#bd7645";ctx.setLineDash([6,3]);ctx.lineWidth=2;ctx.stroke();ctx.setLineDash([]);
    for(const p of draftPolygon){const s=coordToScreen(p[0],p[1]);ctx.beginPath();ctx.arc(s.x,s.y,4,0,7);ctx.fillStyle="#bd7645";ctx.fill();}
  }
}
function fmtAxisTick(t,step) {
  const year=axisToHistorical(t);
  if(step>=1)return historicalYearLabel(year);
  const month=clamp(Math.floor((t-Math.floor(t))*12)+1,1,12);
  return String(month).padStart(2,"0")+"/"+historicalYearLabel(year);
}
function tickStep(raw) {
  const factors=[1,2,2.5,5,10];
  const n=Math.floor(Math.log10(raw));
  let best=1;
  let dist=Infinity;
  for(let k=n-1;k<=n+1;k++)for(const f of factors){
    const v=f*10**k,d=Math.abs(Math.log(v/raw));
    if(d<dist){dist=d;best=v;}
  }
  return best;
}
function axisToX(year){return (year-(timeline.center-timeline.span/2))/timeline.span*rulerW;}
function drawRuler(){
  if(!rulerW||!rulerH)return;
  const ctx=timeCtx;ctx.clearRect(0,0,rulerW,rulerH);
  ctx.fillStyle="#fcfdfb";ctx.fillRect(0,0,rulerW,rulerH);
  const step=tickStep(timeline.span/Math.max(3,rulerW/100));
  const min=timeline.center-timeline.span/2,max=timeline.center+timeline.span/2;
  const mid=37;
  ctx.strokeStyle="#9aac9f";ctx.lineWidth=.8;
  ctx.beginPath();ctx.moveTo(0,mid);ctx.lineTo(rulerW,mid);ctx.stroke();
  ctx.textAlign="center";ctx.font="11px system-ui";
  for(let t=Math.ceil(min/step)*step;t<=max;t+=step){
    const x=axisToX(t);if(x<0||x>rulerW)continue;
    ctx.strokeStyle="#c7d3c8";ctx.beginPath();ctx.moveTo(x,mid-8);ctx.lineTo(x,mid+18);ctx.stroke();
    ctx.fillStyle="#506a62";ctx.fillText(fmtAxisTick(t,step),x,mid-15);
  }
  renderedTime=[];
  for(const e of data.entries){
    if(e.type!=="periodizare")continue;
    const st=dateAxis(e),en=dateAxis(e,true);
    if(st===null)continue;
    const x1=axisToX(st),x2=axisToX(en??st);
    if(x2<0||x1>rulerW)continue;
    ctx.fillStyle=e.id===selectedId?"#c79e69":"#b2d3c4";
    const bx=clamp(x1,0,rulerW),ex=clamp(x2,0,rulerW);
    ctx.fillRect(bx,52,Math.max(3,ex-bx),13);
    ctx.font="10px system-ui";ctx.fillStyle="#496f62";ctx.textAlign="left";
    if(ex-bx>55)ctx.fillText(e.title.slice(0,Math.floor((ex-bx)/6)),bx+3,62);
    renderedTime.push({x1:bx,x2:Math.max(bx+9,ex),y:58,entryId:e.id});
  }
  for(const e of data.entries){
    if(e.type==="periodizare")continue;
    const x=dateAxis(e);
    if(x===null||x<min||x>max)continue;
    const px=axisToX(x);
    ctx.beginPath();ctx.arc(px,mid,selectedId===e.id?5:2.7,0,7);
    ctx.fillStyle=selectedId===e.id?"#bc8650":"#318173";ctx.fill();
    renderedTime.push({x1:px-7,x2:px+7,y:mid,entryId:e.id});
  }
  const central=axisToX(timeline.center);
  ctx.beginPath();ctx.moveTo(central-5,0);ctx.lineTo(central+5,0);ctx.lineTo(central,7);
  ctx.fillStyle="#b38548";ctx.fill();
  $("rangeLabel").textContent=fmtAxisTick(min,step)+" — "+fmtAxisTick(max,step);
  $("timeScale").textContent=step>=1?(step>=100?step+" ani":step+" a"):(Math.round(step*12)+" luni");
  const periodCount=data.entries.filter(e=>e.type==="periodizare").length;
  $("periodNote").textContent=periodCount
    ? periodCount+" periodizări documentate (poți păstra opinii diferite ale autorilor)"
    : "Periodizările apar numai dacă sunt adăugate dintr-o sursă.";
}
function draw() {
  drawScene();drawRuler();
  $("mapState").textContent="Hartă de referință actuală · offline · "+
    Math.abs(Math.round(map.lat))+"°"+(map.lat>=0?"N":"S")+" / "+
    Math.abs(Math.round(map.lon))+"°"+(map.lon>=0?"E":"V");
}
function queryOptions(){
  return {search:$("searchInput").value, type:$("typeFilter").value,sourceId:$("sourceFilter").value,
    center:timeline.center,span:timeline.span,timeOnly:$("timeOnly").checked,sort:$("sortFilter").value};
}
function cite(p) {
  if(!p)return "Trimitere indisponibilă";
  return [p.chapter,p.pageStart?("p. "+p.pageStart+(p.pageEnd&&p.pageEnd!==p.pageStart?"–"+p.pageEnd:"")):"",
    p.paragraph?"§ "+p.paragraph:"",p.sentence?"propoziția "+p.sentence:"",p.line?"rândul "+p.line:""].filter(Boolean).join(" · ")||"Localizare necompletată";
}
function getCites(entry) {
  return (entry?.passageIds||[]).map(id=>passageOf(id)).filter(Boolean).map(p=>({p,s:sourceOf(p.sourceId)}));
}
function renderSelects(){
  const opts=data.sources.slice().sort((a,b)=>a.title.localeCompare(b.title,"ro"))
    .map(s=>'<option value="'+esc(s.id)+'">'+esc(s.author?(s.author+" — "+s.title):s.title)+'</option>').join("");
  $("entrySource").innerHTML='<option value="">— Alege o sursă —</option>'+opts;
  $("sourceFilter").innerHTML='<option value="all">Orice sursă</option>'+opts;
  const popt=data.passages.slice().sort((a,b)=>b.createdAt?.localeCompare(a.createdAt||"")||0)
    .map(p=>'<option value="'+esc(p.id)+'">'+esc((sourceOf(p.sourceId)?.title||"Sursă")+
      " · "+cite(p)+" · "+p.quote.slice(0,64))+'</option>').join("");
  $("existingPassage").innerHTML='<option value="">— Fragment nou —</option>'+popt;
  $("relationEvidence").innerHTML='<option value="">— Alege fragmentul care afirmă legătura —</option>'+popt;
  const eopts=data.entries.map(e=>'<option value="'+esc(e.id)+'">'+esc(e.title)+'</option>').join("");
  $("relationFrom").innerHTML='<option value="">— Fișa de plecare —</option>'+eopts;
  $("relationTo").innerHTML='<option value="">— Fișa asociată —</option>'+eopts;
}
function renderTabs(){
  $("entryCount").textContent=data.entries.length;
  $("sourceCount").textContent=data.sources.length;
  $("relationCount").textContent=data.relations.length;
  document.querySelectorAll("[data-tab]").forEach(b=>b.classList.toggle("active",b.dataset.tab===tab));
  $("entryFilters").classList.toggle("hidden",tab!=="entries");
}
function sourceMatches(s){
  const terms=textKey($("searchInput").value).split(/\s+/).filter(Boolean);
  return terms.every(t=>textKey([s.title,s.author,s.speciality,s.publication,s.bibliography].join(" ")).includes(t));
}
function cardMarkup({type,title,subtitle,meta,id,action}){
  return '<button type="button" class="list-card '+(id===selectedId?"active":"")+
    '" data-card="'+esc(id)+'" data-action="'+action+'">'+
    '<div class="item-overline">'+esc(type)+'</div><h3>'+esc(title)+'</h3>'+
    '<p>'+esc(subtitle||"")+'</p><div class="item-meta">'+esc(meta||"")+'</div></button>';
}
function renderList(){
  renderTabs();
  const box=$("libraryList");
  if(tab==="entries"){
    const entries=queryEntries(data,queryOptions());
    box.innerHTML=entries.length ? entries.map(e=>{
      const cs=getCites(e), p=cs[0]?.p,s=cs[0]?.s;
      return cardMarkup({type:types[e.type]||e.type,title:e.title,id:e.id,action:"entry",
        subtitle:e.paraphrase||p?.quote||"Fără descriere",
        meta:dateLabel(e)+"　·　"+(s?.author||s?.title||"Sursă")+"　"+(p?.pageStart?"p. "+p.pageStart:"")});
    }).join(""):emptyList(data.entries.length?"Niciun rezultat pentru aceste criterii.":"Începe cu o sursă și prima fișă.",
      data.entries.length?"Modifică intervalul temporal sau filtrele.":"Fișele apar aici și pe hartă, cu trimiterea exactă la text.");
    $("filterStatus").textContent=entries.length+" / "+data.entries.length+" fișe";
  }else if(tab==="sources"){
    const srcs=data.sources.filter(sourceMatches);
    box.innerHTML=srcs.length?srcs.map(s=>{
      const count=data.passages.filter(p=>p.sourceId===s.id).length;
      return cardMarkup({type:"SURSĂ · "+count+" fragmente",title:s.title,subtitle:s.bibliography||s.speciality,
        meta:[s.author,s.publication,s.edition].filter(Boolean).join(" · "),id:s.id,action:"source"});
    }).join(""):emptyList("Nicio sursă înregistrată.","Folosește butonul „＋ Sursă” pentru catalog.");
    $("filterStatus").textContent=srcs.length+" / "+data.sources.length+" surse";
  }else{
    const results=data.relations.filter(r=>textKey([r.kind,entryOf(r.fromId)?.title,entryOf(r.toId)?.title].join(" "))
      .includes(textKey($("searchInput").value)));
    box.innerHTML=results.length?results.map(r=>cardMarkup({type:"RELAȚIE EXPLICITĂ",title:r.kind,
      subtitle:(entryOf(r.fromId)?.title||"?")+" → "+(entryOf(r.toId)?.title||"?"),
      meta:cite(passageOf(r.passageId)),id:r.id,action:"relation"})).join(""):
      emptyList("Nu sunt relații înregistrate.","Leagă fișe îndepărtate doar când legătura este explicită.");
    $("filterStatus").textContent=results.length+" / "+data.relations.length+" relații";
  }
  box.querySelectorAll("[data-card]").forEach(b=>b.onclick=()=> {
    const id=b.dataset.card;
    if(b.dataset.action==="entry")openEntry(id);
    if(b.dataset.action==="source")openSource(id);
    if(b.dataset.action==="relation")openRelation(id);
  });
  scheduleDraw();
}
function emptyList(title,sub){
  return '<div class="empty-state"><div class="empty-icon">⌑</div><strong>'+esc(title)+
    '</strong><p>'+esc(sub)+'</p></div>';
}
function openPanel(markup){
  $("detailContent").innerHTML=markup;$("detailPanel").classList.remove("hidden");
  $("detailPanel").scrollTop=0;
}
function hideDetail(){
  $("detailPanel").classList.add("hidden");selectedId=null;selectedSource=null;
  renderList();scheduleDraw();
}
function openEntry(id) {
  const e=entryOf(id);if(!e)return;
  selectedId=e.id;selectedSource=null;
  const citations=getCites(e);
  const chunks=citations.map(({p,s},i)=>'<div class="detail-source"><strong>'+
    esc(s?.title||"Sursă indisponibilă")+'</strong><span>'+esc([s?.author,cite(p)].filter(Boolean).join(" · "))+
    '</span><div class="detail-quote">'+htmlLines(p.quote)+'</div></div>').join("");
  const tags=uniqueTerms([...(e.topics||[]),...(e.indexes||[]),...uniqueTerms(e.people||"")]);
  const related=data.relations.filter(r=>r.fromId===id||r.toId===id);
  openPanel('<div class="detail-kicker">'+esc(types[e.type]||e.type)+
    ' · FIȘĂ DOCUMENTATĂ</div><h2>'+esc(e.title)+'</h2><div class="detail-date">'+esc(dateLabel(e))+
    '</div><div class="detail-meta">'+esc([e.place,e.people].filter(Boolean).join(" · "))+
    '</div>'+(e.paraphrase?'<h3>Parafrază introdusă manual</h3><p class="detail-meta">'+htmlLines(e.paraphrase)+'</p>':"")+
    (tags.length?'<h3>Acces multidimensional</h3>'+tags.map(s=>'<span class="index-chip">'+esc(s)+'</span>').join(""):"")+
    '<h3>Fragmente originale · '+citations.length+' trimiteri</h3>'+chunks+
    (related.length?'<h3>Relații susținute textual</h3>'+related.map(r=>{
      const other=entryOf(r.fromId===id?r.toId:r.fromId);
      return '<button type="button" class="detail-related" data-go="'+esc(other?.id||"")+'">'+
        esc(r.kind+' ↗ '+(other?.title||"?"))+'</button>';
    }).join(""):"")+
    '<div class="detail-actions"><button type="button" class="button primary" id="detailEdit">✎ Editează fișa</button>'+
    '<button type="button" class="button outline" id="detailAddEvidence">＋ Dovadă</button>'+
    '<button type="button" class="button outline" id="detailLink">↗ Relație</button>'+
    '<button type="button" class="button flat" id="detailDelete">Șterge fișa</button></div>');
  $("detailEdit").onclick=()=>openEntryEditor(e.id);
  $("detailAddEvidence").onclick=()=>openEntryEditor(e.id,true);
  $("detailLink").onclick=()=>openRelationEditor(e.id);
  $("detailDelete").onclick=()=>deleteEntry(e.id);
  $("detailContent").querySelectorAll("[data-go]").forEach(el=>el.onclick=()=>openEntry(el.dataset.go));
  if(e.lat!=null&&e.lon!=null){map.lon=Number(e.lon);map.lat=Number(e.lat);scheduleDraw();}
  renderList();
}
function openSource(id){
  const s=sourceOf(id);if(!s)return;
  selectedId=null;selectedSource=id;
  const passages=data.passages.filter(p=>p.sourceId===id);
  const entryIds=new Set(passages.flatMap(p=>data.entries.filter(e=>e.passageIds?.includes(p.id)).map(e=>e.id)));
  const entries=queryEntries(data,{sort:"source"}).filter(e=>entryIds.has(e.id));
  openPanel('<div class="detail-kicker">CATALOGUL SURSELOR</div><h2>'+esc(s.title)+'</h2>'+
    '<div class="detail-meta">'+esc([s.author,s.speciality,s.publication,s.edition].filter(Boolean).join(" · "))+'</div>'+
    (s.bibliography?'<h3>Referința bibliografică</h3><p class="detail-meta">'+htmlLines(s.bibliography)+'</p>':"")+
    '<h3>Parcurgere în ordinea sursei</h3><p class="detail-meta">'+passages.length+' fragmente · '+entries.length+' fișe asociate</p>'+
    entries.map(e=>'<button class="detail-related" type="button" data-go="'+esc(e.id)+'">'+esc(e.title)+'</button>').join("")+
    '<div class="detail-actions"><button class="button primary" id="editSource" type="button">✎ Editează sursa</button>'+
    '<button class="button outline" id="newEntryForSource" type="button">＋ Fișă din sursă</button></div>');
  $("editSource").onclick=()=>openSourceEditor(id);
  $("newEntryForSource").onclick=()=>openEntryEditor(null,false,id);
  $("detailContent").querySelectorAll("[data-go]").forEach(el=>el.onclick=()=>openEntry(el.dataset.go));
  renderList();
}
function openRelation(id){
  const r=data.relations.find(x=>x.id===id);if(!r)return;
  const p=passageOf(r.passageId),s=sourceOf(p?.sourceId);
  openPanel('<div class="detail-kicker">RELAȚIE EXPLICITĂ · TEXT VERIFICABIL</div><h2>'+esc(r.kind)+'</h2>'+
    '<button class="detail-related" data-go="'+esc(r.fromId)+'">'+esc(entryOf(r.fromId)?.title)+'</button>'+
    '<div class="detail-meta">↓</div><button class="detail-related" data-go="'+esc(r.toId)+'">'+esc(entryOf(r.toId)?.title)+'</button>'+
    '<h3>Textul care susține relația</h3><div class="detail-source"><strong>'+esc(s?.title)+'</strong>'+
    '<span>'+esc(cite(p))+'</span><div class="detail-quote">'+htmlLines(p?.quote||"")+'</div></div>');
  $("detailContent").querySelectorAll("[data-go]").forEach(el=>el.onclick=()=>openEntry(el.dataset.go));
}
async function deleteEntry(id){
  if(!confirm("Ștergi această fișă? Fragmentele originale rămân în baza documentară; relațiile fișei vor fi șterse."))return;
  try{
    for(const r of data.relations.filter(r=>r.fromId===id||r.toId===id))await removeObject("relations",r.id);
    await removeObject("entries",id);await reload();
    hideDetail();notice("Fișa a fost eliminată.");
  }catch(e){notice("Eroare: "+e.message);}
}
function setTab(next){tab=next;renderList();}
function setTimeline(center,span=timeline.span){
  timeline.span=clamp(span,.083333,20000);
  timeline.center=clamp(center,-10000,3000);
  renderList();scheduleDraw();
}
async function reload(){
  data=await loadData();
  const oldSource=$("sourceFilter").value;
  renderSelects();
  if(data.sources.some(s=>s.id===oldSource))$("sourceFilter").value=oldSource;
  renderList();
  if(selectedId&&!entryOf(selectedId))hideDetail();
}
function showDialog(kind){
  closeMenu();
  $("sourceForm").classList.toggle("hidden",kind!=="source");
  $("entryForm").classList.toggle("hidden",kind!=="entry");
  $("relationForm").classList.toggle("hidden",kind!=="relation");
  $("dialogTitle").textContent=kind==="source"?(currentSourceId?"Editează sursa":"Sursă nouă"):
    kind==="entry"?(currentEntryId?"Editează fișa":"Fișă documentară nouă"):"Relație explicită nouă";
  $("editorDialog").showModal();
}
function read(form,name){return form.elements.namedItem(name)?.value?.trim()||"";}
function write(form,name,value){const item=form.elements.namedItem(name);if(item)item.value=value??"";}
function openSourceEditor(id=null){
  currentSourceId=id;
  const f=$("sourceForm");f.reset();
  const s=id?sourceOf(id):null;
  if(s)for(const name of ["title","author","speciality","publication","edition","bibliography"])write(f,name,s[name]);
  showDialog("source");
}
function updateEvidenceSelector(){
  const id=$("existingPassage").value;
  $("newPassageFields").classList.toggle("hidden",Boolean(id));
  if(id){
    const p=passageOf(id),s=sourceOf(p?.sourceId);
    $("currentEvidence").classList.remove("hidden");
    $("currentEvidence").textContent=(s?.title||"Sursă")+" · "+cite(p)+"\n"+(p?.quote||"");
  }else{$("currentEvidence").classList.add("hidden");}
}
function openEntryEditor(id=null,addEvidence=false,forcedSource=null){
  if(!data.sources.length){notice("Înregistrează mai întâi o sursă.");openSourceEditor();return;}
  const f=$("entryForm");
  if(!id||currentEntryId!==id)f.reset();
  currentEntryId=id;
  const e=id?entryOf(id):null;
  if(e){
    for(const name of ["title","type","place","people","paraphrase","yearStart","yearEnd","month","day","dateText","lat","lon"])
      write(f,name,e[name]);
    write(f,"topics",(e.topics||[]).join(", "));
    write(f,"indexes",(e.indexes||[]).join(", "));
    write(f,"geometry",(e.geometry||[]).map(p=>p.join(",")).join("; "));
    $("existingPassage").value=addEvidence?"":e.passageIds?.[0]||"";
  }else{
    f.reset();
    $("existingPassage").value="";
    if(forcedSource)write(f,"sourceId",forcedSource);
  }
  if(addEvidence){$("existingPassage").value="";write(f,"quote","");}
  updateEvidenceSelector();showDialog("entry");
}
function openRelationEditor(fromId=null){
  if(data.entries.length<2){notice("Ai nevoie de cel puțin două fișe.");return;}
  $("relationForm").reset();
  if(fromId)$("relationFrom").value=fromId;
  const from=entryOf(fromId);
  $("relationEvidence").value=from?.passageIds?.[0]||"";
  showDialog("relation");
}
async function saveSource(event){
  event.preventDefault();const f=event.currentTarget;
  const title=read(f,"title");if(!title){notice("Titlul sursei este obligatoriu.");return;}
  const old=currentSourceId?sourceOf(currentSourceId):null;
  const s={id:old?.id||newId(),createdAt:old?.createdAt||new Date().toISOString()};
  for(const name of ["title","author","speciality","publication","edition","bibliography"])s[name]=read(f,name);
  try{
    await putObjects([{table:"sources",value:s}]);
    $("editorDialog").close();currentSourceId=null;
    await reload();setTab("sources");openSource(s.id);notice("Sursa a fost salvată o singură dată.");
  }catch(err){notice("Nu s-a putut salva: "+err.message);}
}
async function saveEntry(event){
  event.preventDefault();
  const f=event.currentTarget;
  const title=read(f,"title");
  if(!title){notice("Completează denumirea fișei.");return;}
  const st=numberOrNull(read(f,"yearStart")),end=numberOrNull(read(f,"yearEnd"));
  if((st!==null&&historicalToAxis(st)===null)||(end!==null&&historicalToAxis(end)===null)){
    notice("Anul trebuie să fie întreg și diferit de zero.");return;
  }
  if(st!==null&&end!==null&&historicalToAxis(end)<historicalToAxis(st)){
    notice("Sfârșitul intervalului este anterior începutului.");return;
  }
  const lat=numberOrNull(read(f,"lat")),lon=numberOrNull(read(f,"lon"));
  if((lat!=null&&(lat< -90||lat>90))||(lon!=null&&(lon< -180||lon>180))||
    (lat===null)!==(lon===null)){notice("Introdu ambele coordonate valide sau lasă-le libere.");return;}
  let geometry;try{geometry=parseGeometry(read(f,"geometry"));}catch(err){notice(err.message);return;}
  const old=currentEntryId?entryOf(currentEntryId):null;
  const pids=[...(old?.passageIds||[])];
  const existingId=read(f,"existingPassage");
  const writes=[];
  if(existingId){
    if(!passageOf(existingId)){notice("Fragmentul selectat nu mai există.");return;}
    if(!pids.includes(existingId))pids.push(existingId);
  }else{
    const sourceId=read(f,"sourceId"),quote=f.elements.namedItem("quote").value;
    if(!sourceId||!sourceOf(sourceId)||!quote.trim()){
      if(!old||!pids.length){notice("O fișă necesită o sursă și textul exact al unui fragment.");return;}
      // Modificarea metadatelor unei fișe deja documentate nu necesită citat nou.
    }else{
      const candidate={sourceId,quote};
      for(const name of ["chapter","pageStart","pageEnd","paragraph","sentence","line"])candidate[name]=read(f,name);
      const reused=findExistingPassage(data.passages,candidate);
      const passage=reused||{...candidate,id:newId(),createdAt:new Date().toISOString()};
      if(!pids.includes(passage.id))pids.push(passage.id);
      if(!reused)writes.push({table:"passages",value:passage});
    }
  }
  if(!pids.length){notice("Nu poți salva o fișă fără fragment textual.");return;}
  const entry={id:old?.id||newId(),createdAt:old?.createdAt||new Date().toISOString(),
    updatedAt:new Date().toISOString(),passageIds:pids,title,type:read(f,"type")||"afirmatie",
    place:read(f,"place"),people:read(f,"people"),topics:uniqueTerms(read(f,"topics")),
    indexes:uniqueTerms(read(f,"indexes")),paraphrase:read(f,"paraphrase"),
    yearStart:st,yearEnd:end,month:numberOrNull(read(f,"month")),
    day:numberOrNull(read(f,"day")),dateText:read(f,"dateText"),lat,lon,geometry};
  writes.push({table:"entries",value:entry});
  try{
    await putObjects(writes);$("editorDialog").close();currentEntryId=null;
    await reload();setTab("entries");openEntry(entry.id);
    notice(writes.some(x=>x.table==="passages")?"Fragment și fișă salvate.":"Fișa salvată fără duplicarea fragmentului.");
  }catch(err){notice("Nu s-a putut salva: "+err.message);}
}
async function saveRelation(event){
  event.preventDefault();const f=event.currentTarget;
  const fromId=read(f,"fromId"),toId=read(f,"toId"),
    passageId=read(f,"passageId"),kind=read(f,"kind");
  if(fromId===toId||!entryOf(fromId)||!entryOf(toId)||!passageOf(passageId)||!kind){
    notice("Alege două fișe diferite și un fragment care dovedește relația.");return;
  }
  if(data.relations.some(r=>r.fromId===fromId&&r.toId===toId&&textKey(r.kind)===textKey(kind)&&r.passageId===passageId)){
    notice("Relația este deja înregistrată.");return;
  }
  const relation={id:newId(),fromId,toId,passageId,kind,createdAt:new Date().toISOString()};
  try{
    await putObjects([{table:"relations",value:relation}]);
    $("editorDialog").close();await reload();setTab("relations");
    openRelation(relation.id);notice("Relația documentată a fost păstrată.");
  }catch(e){notice(e.message);}
}
function formatMapPoint(p){return p.lon.toFixed(3)+","+p.lat.toFixed(3);}
function restoreEditor(){mode=null;$("drawBar").classList.add("hidden");$("editorDialog").showModal();scheduleDraw();}
function mapTap(pos) {
  if(mode==="point"){
    const p=screenToCoord(pos.x,pos.y),f=$("entryForm");
    write(f,"lon",p.lon.toFixed(5));write(f,"lat",p.lat.toFixed(5));
    restoreEditor();notice("Punctul geografic a fost preluat în fișă.");
    return;
  }
  if(mode==="polygon"){
    const p=screenToCoord(pos.x,pos.y);
    draftPolygon.push([Number(p.lon.toFixed(5)),Number(p.lat.toFixed(5))]);
    scheduleDraw();return;
  }
  const hit=renderedDots.map(g=>({...g,dist:Math.hypot(g.x-pos.x,g.y-pos.y)}))
    .filter(g=>g.dist<21).sort((a,b)=>a.dist-b.dist)[0];
  if(hit){
    if(hit.items.length===1)openEntry(hit.items[0].id);
    else{
      openPanel('<div class="detail-kicker">SUPRAPUNERE CONTROLATĂ</div><h2>'+
        hit.items.length+' fișe în aceeași poziție</h2><p class="detail-meta">Nicio înregistrare nu a fost dublată. Alege informația dorită.</p>'+
        hit.items.map(e=>'<button type="button" class="detail-related" data-go="'+esc(e.id)+'">'+
          esc(dateLabel(e)+" · "+e.title)+'</button>').join(""));
      $("detailContent").querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>openEntry(b.dataset.go));
    }
  }
}
function setupMapInput(){
  scene.addEventListener("pointerdown",e=>{
    scene.setPointerCapture(e.pointerId);
    mapPointers.set(e.pointerId,{x:e.offsetX,y:e.offsetY});
    mapLast={x:e.offsetX,y:e.offsetY};mapWasDragged=false;
  });
  scene.addEventListener("pointermove",e=>{
    if(!mapPointers.has(e.pointerId))return;
    const before=mapPointers.get(e.pointerId);
    mapPointers.set(e.pointerId,{x:e.offsetX,y:e.offsetY});
    if(mapPointers.size===2){
      const pts=[...mapPointers.values()],other=[...mapPointers.entries()].find(([id])=>id!==e.pointerId)?.[1];
      if(other){
        const prev=Math.hypot(before.x-other.x,before.y-other.y);
        const now=Math.hypot(e.offsetX-other.x,e.offsetY-other.y);
        if(prev>4&&now>4)zoomMap(now/prev,(e.offsetX+other.x)/2,(e.offsetY+other.y)/2);
      }
      mapWasDragged=true;return;
    }
    const dx=e.offsetX-before.x,dy=e.offsetY-before.y;
    if(Math.abs(dx)+Math.abs(dy)>0.5){
      map.lon=clamp(map.lon-dx/mapScale(),-180,180);
      map.lat=clamp(map.lat+dy/mapScale(),-85,85);
      if(Math.hypot(e.offsetX-mapLast.x,e.offsetY-mapLast.y)>7)mapWasDragged=true;
      scheduleDraw();
    }
  });
  scene.addEventListener("pointerup",e=>{
    if(!mapWasDragged&&mapPointers.size===1)mapTap({x:e.offsetX,y:e.offsetY});
    mapPointers.delete(e.pointerId);mapLast=null;
  });
  scene.addEventListener("pointercancel",e=>mapPointers.delete(e.pointerId));
  scene.addEventListener("wheel",e=>{e.preventDefault();zoomMap(e.deltaY<0?1.22:1/1.22,e.offsetX,e.offsetY);},{passive:false});
}
function setupRulerInput(){
  ruler.addEventListener("pointerdown",e=>{
    ruler.setPointerCapture(e.pointerId);timeDrag={x:e.offsetX,origin:timeline.center,moved:false};
  });
  ruler.addEventListener("pointermove",e=>{
    if(!timeDrag)return;
    const dx=e.offsetX-timeDrag.x;
    if(Math.abs(dx)>4)timeDrag.moved=true;
    timeline.center=clamp(timeDrag.origin-dx/rulerW*timeline.span,-10000,3000);
    renderList();scheduleDraw();
  });
  ruler.addEventListener("pointerup",e=>{
    if(timeDrag&&!timeDrag.moved){
      const hit=renderedTime.find(x=>e.offsetX>=x.x1&&e.offsetX<=x.x2&&Math.abs(e.offsetY-x.y)<11);
      if(hit)openEntry(hit.entryId);
    }
    timeDrag=null;
  });
  ruler.addEventListener("pointercancel",()=>timeDrag=null);
  ruler.addEventListener("wheel",e=>{
    e.preventDefault();
    setTimeline(timeline.center,timeline.span*(e.deltaY>0?1.5:1/1.5));
  },{passive:false});
}
function archiveDownload(text) {
  const blob=new Blob([text],{type:"application/json;charset=utf-8"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download="historylab-arhiva-"+new Date().toISOString().slice(0,10)+".json";
  document.body.appendChild(a);a.click();a.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function exportArchive(){
  try{
    const backup=await makeBackup(),content=JSON.stringify(backup,null,2);
    if(window.HistoryBridge&&typeof window.HistoryBridge.saveJson==="function")
      window.HistoryBridge.saveJson(content);
    else archiveDownload(content);
    notice("Arhiva completă este pregătită pentru salvare.");
  }catch(e){notice("Export nereușit: "+e.message);}
}
async function importArchive(event){
  const file=event.target.files?.[0];
  event.target.value="";if(!file)return;
  try{
    const backup=JSON.parse(await file.text());
    if(!confirm("IMPORT: înlocuiești toate sursele și fișele de pe acest dispozitiv cu arhiva selectată. Continuăm?"))return;
    await replaceData(backup);hideDetail();await reload();
    notice("Arhiva a fost importată și verificată.");
  }catch(e){notice("Import oprit: "+e.message);}
}
function bind(){
  $("newEntryButton").onclick=()=>openEntryEditor();
  $("newSourceButton").onclick=()=>openSourceEditor();
  $("menuNewSource").onclick=()=>openSourceEditor();
  $("menuNewRelation").onclick=()=>openRelationEditor();
  $("exportButton").onclick=$("menuExport").onclick=exportArchive;
  $("importButton").onclick=$("menuImport").onclick=()=>{
    closeMenu();$("fileImport").click();
  };
  $("fileImport").addEventListener("change",importArchive);
  $("moreButton").onclick=e=>{e.stopPropagation();$("actionMenu").classList.toggle("hidden");};
  document.addEventListener("click",e=>{
    if(!$("actionMenu").contains(e.target)&&e.target!==$("moreButton"))closeMenu();
  });
  $("detailClose").onclick=hideDetail;
  $("dialogClose").onclick=$("cancelEditor").onclick=$("cancelRelation").onclick=()=>$("editorDialog").close();
  $("sourceForm").onsubmit=saveSource;
  $("entryForm").onsubmit=saveEntry;
  $("relationForm").onsubmit=saveRelation;
  $("existingPassage").onchange=updateEvidenceSelector;
  $("pickPoint").onclick=()=>{
    $("editorDialog").close();mode="point";
    $("drawBar").classList.remove("hidden");
    $("drawBar").querySelector("strong").textContent="Alege un punct";
    $("drawBar").querySelector("span").textContent="Apasă pe hartă pentru coordonatele exacte.";
    $("finishPolygon").classList.add("hidden");notice("Apasă pe hartă pentru poziție.");
  };
  $("startPolygon").onclick=()=>{
    $("editorDialog").close();mode="polygon";draftPolygon=[];
    $("drawBar").classList.remove("hidden");
    $("drawBar").querySelector("strong").textContent="Contur din sursă";
    $("drawBar").querySelector("span").textContent="Apasă succesiv pe hartă: minimum 3 puncte.";
    $("finishPolygon").classList.remove("hidden");notice("Desenează numai forma susținută de sursă.");
  };
  $("cancelPolygon").onclick=()=>{draftPolygon=[];restoreEditor();};
  $("finishPolygon").onclick=()=>{
    if(draftPolygon.length<3){notice("Sunt necesare minimum trei puncte.");return;}
    write($("entryForm"),"geometry",draftPolygon.map(p=>p.join(",")).join("; "));
    draftPolygon=[];restoreEditor();notice("Conturul a fost atașat fișei.");
  };
  $("mapZoomIn").onclick=()=>zoomMap(1.5);
  $("mapZoomOut").onclick=()=>zoomMap(1/1.5);
  $("mapEurope").onclick=()=>{map={lon:19,lat:47,zoom:3.4};scheduleDraw();};
  $("mapWorld").onclick=()=>{map={lon:0,lat:0,zoom:1};scheduleDraw();};
  $("timeBack").onclick=()=>setTimeline(timeline.center-timeline.span*.2);
  $("timeForward").onclick=()=>setTimeline(timeline.center+timeline.span*.2);
  $("timeIn").onclick=()=>setTimeline(timeline.center,timeline.span/2);
  $("timeOut").onclick=()=>setTimeline(timeline.center,timeline.span*2);
  for(const id of ["searchInput","typeFilter","sourceFilter","sortFilter","timeOnly"]){
    $(id).addEventListener(["searchInput"].includes(id)?"input":"change",renderList);
  }
  document.querySelectorAll("[data-tab]").forEach(b=>b.onclick=()=>setTab(b.dataset.tab));
  $("toggleLibrary").onclick=()=>{$("libraryPanel").classList.toggle("collapsed");};
  $("mobileIndex").onclick=()=>{$("libraryPanel").classList.remove("collapsed");};
  window.addEventListener("resize",resize);
  $("editorDialog").addEventListener("close",()=>{
    // Fără ștergerea datelor din editor dacă utilizatorul folosește harta.
    closeMenu();
  });
  setupRulerInput();setupMapInput();
}
async function initialize(){
  bind();resize();
  try{
    data=await loadData();renderSelects();renderList();
  }catch(e){notice("Stocarea locală nu este disponibilă: "+e.message);}
  try{
    const response=await fetch("./world.geojson");
    if(!response.ok)throw new Error("Harta lipsește");
    world=await response.json();
    if(!world?.features)throw new Error("Date geografice invalide");
    scheduleDraw();
  }catch(e){notice("Geografia offline nu s-a încărcat: "+e.message);}
}
initialize();
