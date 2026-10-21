/* historytool: real local API, no mock search or fabricated citations. */
'use strict';
const $=q=>document.querySelector(q);
const S={tab:'index',state:{sources:[],counts:{}},entities:[],lexemes:[],statements:[],indexMode:'entități',entityFilter:'',entityKind:'toate',chosen:[],focus:null,detail:null,overlap:null,layers:null,year:1475,yearActive:false,grain:'ani',month:6,day:12,level:1,claims:[],frame:null,query:'',themes:[],results:null,notes:[],noteId:null,noteTitle:'',noteBody:'',viewId:null,busy:false,ocrEnabled:!!window.HistorytoolMobile};
const openLocalFile=(url)=>{if(window.HistorytoolMobile){window.HistorytoolMobile.saveFile(url)}else{window.open(url,'_blank','noopener')}};
const api=async (url,opts={})=>{const r=await fetch(url,opts);if(!r.ok){let msg='Eroare HTTP '+r.status;try{const j=await r.json();msg=typeof j.detail==='string'?j.detail:JSON.stringify(j.detail||j)}catch{}throw new Error(msg)}const ct=r.headers.get('content-type')||'';return ct.includes('json')?await r.json():r};
const jsonOpts=(method,body)=>({method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
const esc=x=>String(x??'').replace(/[&<>"']/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
const fm=n=>Number(n||0).toLocaleString('ro-RO');
const loc=x=>(x.format==='.pdf'?'PDF p. ':['.png','.jpg','.jpeg'].includes(x.format)?'imagine p. ':'segmentul ')+x.page;
const truncate=(s,n=160)=>{s=String(s??'');return s.length<=n?s:s.slice(0,n-1)+'…'};
const params=x=>Object.entries(x).filter(([,v])=>v!==undefined&&v!==null&&v!=='').map(([k,v])=>encodeURIComponent(k)+'='+encodeURIComponent(v)).join('&');
const e=(t,className,text)=>`<${t}${className?' class="'+className+'"':''}>${esc(text)}</${t}>`;
let toastTimer;
function toast(message){$('#toast').innerHTML=`<div class="message">${esc(message)}</div>`;clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('#toast').innerHTML=''},5200)}
function err(ex){console.error(ex);toast('Eroare: '+(ex.message||ex))}
function setBusy(value,msg){S.busy=value;document.body.classList.toggle('loadingveil',value);if(msg)toast(msg)}
function dateArgs(){if(!S.yearActive)return {};let args={year:S.year};if(['luni','zile'].includes(S.grain))args.month=S.month;if(S.grain==='zile')args.day=S.day;return args}
async function initial(){try{await Promise.all([refreshState(),loadEntities(),loadLayers(),loadNotes(),loadClaims()]);render()}catch(x){err(x);$('#main-content').innerHTML='<div class="empty">Pornirea aplicației a eșuat. Verifică terminalul serverului.</div>'}}
async function refreshState(){S.state=await api('/api/state')}
async function loadEntities(){let url='/api/'+(S.indexMode==='entități'?'entities':S.indexMode==='afirmații'?'statements':'lexemes')+'?'+params({q:S.entityFilter,kind:S.indexMode==='entități'?S.entityKind:undefined,limit:110});let data=await api(url);if(S.indexMode==='entități')S.entities=data.entities;else if(S.indexMode==='afirmații')S.statements=data.statements;else S.lexemes=data.lexemes;}
async function loadLayers(){S.layers=await api('/api/layers?'+params(dateArgs()))}
async function loadDetail(){if(S.chosen.length===0){S.focus=null;S.detail=null;S.overlap=null;return}S.overlap=S.chosen.length>1?await api('/api/overlaps?'+params({...dateArgs(),ids:S.chosen.join(',')})):null;let id=S.focus||S.chosen[0];S.focus=id;S.detail=await api('/api/entity/'+id+'?'+params({...dateArgs(),limit:350}));}
async function loadNotes(){S.notes=(await api('/api/notes')).notes;if(S.noteId&& !S.notes.some(x=>x.id===S.noteId))S.noteId=null;if(S.noteId){let note=S.notes.find(x=>x.id===S.noteId);S.noteTitle=note.title;S.noteBody=note.body;}}

async function loadClaims(){const arg=params(dateArgs());const [claims,frame]=await Promise.all([api('/api/claims?'+arg),api('/api/context?'+arg)]);S.claims=claims.claims;S.frame=frame}
function claimLine(cl){const object=cl.object_name||cl.object_literal;return `<button class="attested-claim" data-act="claim-evidence" data-id="${cl.id}" title="Arată toate atestările și pagina exactă"><strong>${esc(cl.subject)} <span class="predicate">${esc(cl.predicate)}</span> ${esc(object||'')}</strong><small>${cl.place?esc(cl.place)+' · ':''}${cl.year_start===null?'Nedatat':esc(cl.precision)+' '+esc(cl.year_start)} · ${cl.attestations} atestări</small><small>↗ ${esc(truncate(cl.quote,140))}</small></button>`}
function renderVerifiedFrame(){let f=S.frame||{regions:[],intersections:[],unplaced:[],total:0};return `<section class="verified-frame"><div class="verified-heading"><div><span class="caps">CADRU UNIC · AFIRMAȚII VERIFICATE</span><h2>Suprapuneri explicite în corpus</h2></div><span class="pill green">${fm(f.total)} afirmații validate</span></div>
${!f.total?`<div class="empty" style="padding:24px"><strong>Cadru documentar pregătit</strong><p>Deschide un pasaj și înregistrează o relație numai după verificarea formulării originale. Nu se inventează localizări.</p></div>`:''}
<div class="common-space">
${(f.regions||[]).map((r,i)=>`<section class="documented-region" style="--layer-hue:${[207,144,36,277,14][i%5]}"><div class="region-header"><b>${esc(r.name)}</b><span>${r.claims.length} afirmații</span></div><div class="actor-nests">${r.subjects.slice(0,S.level===0?0:S.level===1?8:50).map(x=>`<div class="actor-nest"><span class="actor-title">${esc(x.name)}</span>${x.claims.map(claimLine).join('')}</div>`).join('')}</div></section>`).join('')}
${(f.intersections||[]).map((r,i)=>`<section class="intersection-surface"><div class="cross-frames"><span>${esc(r.names[0])}</span><span>${esc(r.names[1])}</span><b>Suprapunere explicită comună</b></div><div class="shared-intersection">${r.claims.map(claimLine).join('')}</div></section>`).join('')}
${f.unplaced?.length?`<section class="undated-surface"><b>Context spațial neprecizat în afirmație</b><div class="actor-nests">${f.unplaced.map(claimLine).join('')}</div></section>`:''}
</div><p class="right-hint">Acesta nu este un contur geografic sau o reconstituire automată. Fiecare afirmație a fost validată pe un pasaj și poate fi revocată.</p></section>`}

function render(){document.querySelectorAll('.navbtn').forEach(b=>b.classList.toggle('active',b.dataset.tab===S.tab));if(S.tab==='index')renderIndex();else if(S.tab==='search')renderSearch();else renderLab()}
const selectedChip=(x,i)=>`<button class="chip tone${i%5}" data-act="remove-selected" data-id="${x.id}" title="Elimină din selecție">${esc(x.name)} <span class="closechip">×</span></button>`;
const findingResult=(x)=>`<div class="evidence-row"><div class="evidence-text">${esc(truncate(x.text,210))}<div class="evidence-source">${esc(x.source_title)} · ${esc(loc(x))} ${x.time_literal?`· ${esc(x.time_literal)} (${esc(x.precision)})`:'· nedatat'}</div></div><button class="text-button" data-act="view" data-id="${x.id}">Vezi pasajul ↗</button></div>`;
function renderSources(){let sources=S.state.sources||[];return `<div class="panel-heading"><h2>Bibliotecă</h2><span class="pill">${fm(sources.length)} surse</span></div><div class="panel-content">
<div class="uploadbox"><div class="upload-ico">+</div><strong>Adaugă surse istorice</strong><small>PDF · DOCX · JPG · PNG · TXT — fișierele rămân locale</small><button class="btn primary block" data-act="pick-files">＋ Atașează fișiere</button></div>
<div class="headerrow" style="margin-top:12px"><button class="btn block" data-act="run-index" ${S.state.counts.pending?'':'disabled'}>⌁ Indexează sursele ${S.state.counts.pending?'('+S.state.counts.pending+')':''}</button></div>
<div class="ocr-option"><label><input id="ocr-enable" type="checkbox" ${S.ocrEnabled?'checked':''}> ${window.HistorytoolMobile?'OCR local pentru PDF-uri și imagini scanate (verifică rezultatul)':'OCR pentru PDF scanate (Tesseract opțional)'}</label></div>
<div class="headerrow" style="margin-top:8px"><span class="subtle tiny">Nu ai surse? Încearcă motorul.</span><button class="text-button" data-act="demo">Date fictive demonstrative</button></div>
<div class="source-actions"><button class="btn sm" data-act="backup">↓ Copie de siguranță</button><button class="btn sm" data-act="verify">✓ Integritate surse</button><button class="btn sm" data-act="audit">Jurnal</button></div>
<div class="statline"><div class="stat"><b>${fm(S.state.counts.passages)}</b><span>pasaje</span></div><div class="stat"><b>${fm(S.state.counts.statements)}</b><span>afirmații unice</span></div><div class="stat"><b>${fm(S.state.counts.lexemes)}</b><span>forme lexicale</span></div></div>
<div class="section-title">Surse încărcate</div><div class="source-list">${sources.length?sources.map(src=>`<div class="source-item"><span class="source-icon">${src.format?.slice(1).toUpperCase()}</span><div style="min-width:0;flex:1"><div class="source-name" title="${esc(src.filename)}">${esc(src.title)}</div><div class="source-info">${esc(src.status==='indexed'?`${src.page_count} pag. · ${src.passage_count} pasaje`:src.status==='pending'?'În așteptarea indexării':src.status==='needs_ocr'?'Nu s-a extras text; verifică OCR-ul':'Eroare la citire')} ${src.warning?'· ⚠ '+esc(truncate(src.warning,100)):''}</div></div><button class="meta-source" data-act="metadata" data-id="${src.id}" title="Fișa bibliografică">✎</button><button class="delete-source" data-act="delete-source" data-id="${src.id}" data-name="${esc(src.filename)}" title="Șterge sursa și atestările ei">×</button></div>`).join(''):'<div class="empty" style="padding:13px">Biblioteca este goală.</div>'}</div>
<div class="section-title">Index universal <button class="text-button" data-act="new-entity">+ Identitate / termen</button></div>
<div class="tabs-sm">${['entități','afirmații','lexeme'].map(k=>`<button class="tab-sm ${S.indexMode===k?'active':''}" data-act="mode" data-mode="${k}">${k[0].toUpperCase()+k.slice(1)}</button>`).join('')}</div>
<div class="input-wrap" style="margin-top:9px"><span class="searchicon">⌕</span><input id="entity-filter" value="${esc(S.entityFilter)}" autocomplete="off" placeholder="Caută în index…" aria-label="Caută în index"></div>
<div class="index-list">${renderIndexList()}</div>
</div>`}
function renderIndexList(){if(S.indexMode==='entități')return S.entities.length?S.entities.slice(0,100).map(x=>`<button class="index-entry ${S.chosen.includes(x.id)?'active':''}" data-act="select-entity" data-id="${x.id}" title="${esc(x.status)} · ${x.sources} surse"><span class="left"><i class="tiny-dot dot-${esc(x.kind)}"></i><span class="entrytitle">${esc(x.name)}</span></span><span class="num">${fm(x.appearances)}</span></button>`).join(''):'<div class="empty">Nu există entități în sursele indexate.</div>';
 if(S.indexMode==='afirmații')return S.statements.length?S.statements.map(x=>`<div style="padding:9px 4px;border-bottom:1px solid #edf2f7;font-size:11px;color:#405773">${esc(truncate(x.text,135))}<span class="pill" style="margin-top:6px">${x.attestations} atestări</span></div>`).join(''):'<div class="empty">Nu există afirmații indexate.</div>';
 return S.lexemes.length?S.lexemes.map(x=>`<div class="index-entry"><span class="entrytitle">${esc(x.form)}</span><span class="num">${fm(x.occurrences)}</span></div>`).join(''):'<div class="empty">Nu există termeni indexați.</div>'}
function renderRuler(){let steps={'ere':1000,'epoci':250,'secole':100,'decenii':10,'ani':1,'luni':1,'zile':1};let step=steps[S.grain]||1;let timeSel=S.yearActive;const months=['ian','feb','mar','apr','mai','iun','iul','aug','sep','oct','noi','dec'];let baseLabel=S.year+(S.grain==='luni'||S.grain==='zile'?' · '+months[S.month-1]:'')+(S.grain==='zile'?' '+S.day:'');let timeInputs=(['luni','zile'].includes(S.grain)?`<select id="month-input" title="Luna selectată" class="yearbox" style="width:75px">${months.map((x,i)=>`<option value="${i+1}" ${S.month===i+1?'selected':''}>${x}</option>`).join('')}</select>`:'')+(S.grain==='zile'?`<input id="day-input" type="number" min="1" max="31" value="${S.day}" class="yearbox" style="width:48px" title="Ziua din lună">`:'');return `<section class="timebox">
<div class="time-head"><strong>Riglă temporală <span class="pill outline">universală</span></strong><div class="time-grains">${['ere','epoci','secole','decenii','ani','luni','zile'].map(a=>`<button data-act="grain" data-grain="${a}" class="grain ${S.grain===a?'selected':''}">${a[0].toUpperCase()+a.slice(1)}</button>`).join('')}</div><div class="time-control"><button class="time-step" title="Perioada precedentă" data-act="year-prev">‹</button><input class="yearbox" type="number" id="year-input" value="${S.year}" aria-label="Anul analizat">${timeInputs}<button class="time-step" data-act="year-next" title="Perioada următoare">›</button><button class="btn sm ${timeSel?'primary':''}" data-act="year-active">${timeSel?'● An activ':'○ Fără filtru'}</button></div></div>
<div class="ruler">${[S.year-2*step,S.year-step,S.year,S.year+step,S.year+2*step].map((v,i)=>`<span class="${i===2?'midpoint':''}">${v}</span>`).join('')}</div><div class="year-caption"><span>${S.grain==='luni'||S.grain==='zile'?'Precizia subanuală este afișată doar dacă sursa o precizează.':'Intervalele documentate rămân la precizia declarată în text.'}</span><span>${timeSel?'Moment ales: '+baseLabel:'Toate perioadele'}</span></div></section>`}
function renderLayerCard(region){let classMap={'persoană':'actor','loc':'place','eveniment':'event'};const items=region.items||[];return `<div class="region"><div class="region-head"><div><h3>${esc(region.name)}</h3><span class="area-tag">Cadru spațial menționat în surse</span></div><span class="pill">${fm(region.evidence_count)} pasaje</span></div>
${S.level>0?`<div class="region-items">${items.length?items.slice(0,S.level===1?8:18).map((x)=>`<button class="nested ${classMap[x.kind]||'event'}" data-act="select-entity" data-id="${x.id}" title="Consemnat în același pasaj. Nu implică automat localizare sau o relație istorică."><strong>${esc(x.name)}</strong><small>${esc(x.kind)}${x.literal?' · '+esc(x.literal):' · fără dată'}</small></button>`).join(''):'<span class="subtle sm">Nu sunt suprapuneri atestate la acest nivel.</span>'}</div>`:''}
<div class="region-footer">${S.level===2?'Deschide un element pentru textul și pagina originale.':'Un singur cadru, apariții multiple · fără săgeți'}</div></div>`}
function renderCanvas(){const r=S.layers?.regions||[];const chosen=S.chosen.map(id=>S.entities.find(x=>x.id===id)||S.detail?.entity).filter(Boolean);return `<section class="panel index-middle">
${renderRuler()}
<div class="canvas"><div class="headline"><div><h1>Suprapuneri documentate</h1><p class="canvas-description">Casete imbricate pe spațiu, timp și afirmații. Totul rămâne legat de textul original.</p></div><span class="pill blue">Din sursele încărcate</span></div>
<div class="legend"><span><i style="background:#79a9da"></i> Cadru spațial</span><span><i style="background:#e6ac5c"></i> Actor</span><span><i style="background:#ae93d5"></i> Alte elemente</span><span>Coapariție ≠ relație istorică</span></div>
${renderVerifiedFrame()}
<details class="raw-context"><summary>Coapariții textuale automate · neverificate ca relații</summary><div class="region-layout">${r.length?r.map(renderLayerCard).join(''):`<div class="empty" style="grid-column:1/-1;padding:76px 15px"><span class="glyph">▣</span>Încarcă și indexează surse pentru a vedea cadrele spațiale documentate. Nu sunt inventate hărți geografice.</div>`}</div></details>
<div class="level-control"><span class="subtle sm" style="margin:auto 6px auto 0">Profunzime:</span>${[['0','General'],['1','Elemente suprapuse'],['2','Detaliat']].map(([n,title])=>`<button class="level-choice ${S.level==n?'on':''}" data-act="level" data-level="${n}">${title}</button>`).join('')}</div>
<div class="evidence-box"><div class="evidence-head"><strong>Selecție universală: ${chosen.length?chosen.length+' elemente':'niciun element'}</strong><span class="pill">${S.yearActive?'Data '+S.year+(S.grain==='luni'||S.grain==='zile'?'/'+S.month:'')+(S.grain==='zile'?'/'+S.day:''):'Toate perioadele'}</span></div><div style="display:flex;gap:6px;flex-wrap:wrap;padding:12px">${chosen.length?chosen.map(selectedChip).join(''):'<span class="subtle sm">Selectează unul sau mai multe elemente din index sau din casete.</span>'}</div>
${S.chosen.length>1?`<div style="padding:0 11px 10px"><span class="pill purple">${S.overlap?.count??0} pasaje comune explicite</span><p class="right-hint">Aici sunt afișate doar pasajele care menționează simultan toate elementele selectate, nu relații deduse.</p></div>${(S.overlap?.appearances||[]).slice(0,24).map(findingResult).join('')||'<div class="empty">Nicio coapariție în același pasaj, la nivelul temporal ales.</div>'}`:''}
</div>
<p class="right-hint">${S.layers?.undated_passages||0} pasaje sunt nedatate. ${S.layers?.unresolved_time||0} pasaje nu au precizia necesară pentru momentul ales. Acestea nu sunt mutate artificial într-o zi sau lună. Localizările trebuie validate de istoric.</p>
</div></section>`}
function renderDetails(){const d=S.detail,ent=d?.entity;return `<aside class="panel details-panel"><div class="panel-heading"><h2>Inspecția dovezii</h2><span class="pill green">Text original</span></div><div class="panel-content">${!ent?`<div class="detailcard"><span class="caps">Index reciproc</span><h3>Selectează un element</h3><p class="subtle sm">Alege un nume sau un cadru și vei vedea într-un singur loc toate aparițiile, suprapunerile textuale și trimiterile.</p></div><div class="lab-tip">O persoană se păstrează ca o singură intrare; fiecare apariție dintr-o sursă rămâne distinctă și verificabilă.</div>`:
`<div class="detailcard"><span class="caps">${esc(ent.kind)} · ${esc(ent.status)}</span><h3>${esc(ent.name)}</h3><div class="detailmeta">${d.appearances.length} pasaje${S.yearActive?' pentru '+S.year:''} · ${d.aliases.length} forme de nume</div><div class="headerrow" style="margin-top:12px"><button class="btn sm" data-act="confirm-entity" data-id="${ent.id}">✓ Confirmă identitatea</button><button class="btn sm" data-act="alias" data-id="${ent.id}">＋ Alias</button></div></div>
<div class="section-title">Suprapuneri ale afirmațiilor <span class="pill">${d.overlaps.length}</span></div><div class="overlap-tags">${d.overlaps.slice(0,15).map((x,i)=>`<button class="chip tone${i%5}" data-act="select-entity" data-id="${x.id}" title="Apare în ${x.shared_passages} pasaje împreună cu ${esc(ent.name)}">${esc(x.name)} <b>${x.shared_passages}</b></button>`).join('')||'<span class="sm subtle">Nu există coapariții indexate.</span>'}</div>
<p class="right-hint">Acestea sunt suprapuneri textuale, nu presupuneri despre loc sau relații.</p>
<div class="section-title">Afirmații confirmate <span class="pill">${S.claims.filter(c=>c.subject_id===ent.id).length}</span></div>
<div class="confirmed-items">${S.claims.filter(c=>c.subject_id===ent.id).slice(0,15).map(claimLine).join('')||'<span class="subtle sm">Nu există încă afirmații validate pentru această entitate.</span>'}</div>
<div class="section-title">Trimiteri exacte <span class="pill">${d.appearances.length}</span></div>
<div class="scroll" style="flex:1">${d.appearances.slice(0,130).map(x=>`<button class="page-ref" data-act="view" data-id="${x.id}"><strong>${esc(x.source_title)} · ${esc(loc(x))} ↗</strong><p>${esc(truncate(x.text,220))}</p><small>${x.time_literal?esc(x.time_literal)+' · '+esc(x.precision):'Nedatat'}</small></button>`).join('')||'<div class="empty">Nu există apariții în intervalul selectat.</div>'}</div>`}</div></aside>`}
function renderIndex(){const main=$('#main-content');main.innerHTML=`<div class="three-col"><aside class="panel sources-panel">${renderSources()}</aside>${renderCanvas()}${renderDetails()}</div>`}
function themeColor(i){return ['#3079ce','#de8750','#45a686','#9c76ce','#cf6878','#428db3'][i%6]}
function renderSearch(){let hasResults=Array.isArray(S.results);let html=`<section class="search-screen"><div class="search-shell ${hasResults?'has-results':''}"><div class="search-eyebrow">✦ &nbsp; Interogare în întreaga bibliografie</div><h1>Ce vrei să găsești în surse?</h1><p class="search-sub">Fără răspunsuri inventate. Doar trimiteri către pasaje, dacă există.</p><div class="large-search"><span class="glass">⌕</span><input id="main-query" placeholder="Scrie o întrebare sau o expresie…" value="${esc(S.query)}" aria-label="Interogare surse"><button class="btn primary" data-act="search-submit">Caută →</button></div>
<div class="theme-tools">${S.themes.map((t,i)=>`<span class="chip tone${(i+1)%5}">${esc(t)}<button class="btn ghost sm" style="padding:0 2px" data-act="remove-theme" data-num="${i}">×</button></span>`).join('')}<button class="btn sm dashed" data-act="add-theme">＋ Adaugă temă paralelă</button><span class="theme-note">Fiecare temă are marcaj distinct.</span></div>
${hasResults?renderResults():`<div class="search-placeholder">Când trimiți întrebarea, aici apare o singură casetă cu trimiteri din sursele indexate. Atinge un tag pentru salt direct la textul original, cu marcaj.</div>`}</div></section>`;$('#main-content').innerHTML=html}
function renderResults(){let results=S.results||[];return results.map((group,i)=>`<div class="results-group"><h3 class="group-title"><span class="theme-color-bar" style="background:${themeColor(i)}"></span>${esc(i===0?'Căutare principală: ':'Temă paralelă: ')} <span class="subtle">${esc(group.query)}</span></h3><div class="results-card"><div class="results-head"><h2>${fm(group.total)} potriviri în corpus · ${fm(group.sources?.length||0)} surse în această pagină</h2><span class="pill outline">${group.total?'Selectează un tag':'Niciun rezultat lexical'}</span></div>
${group.sources?.length?group.sources.map(src=>`<div class="result-source"><div class="result-title"><span>▤ &nbsp; ${esc(src.title)}</span><span class="pill">${fm(src.hits)} trimiteri</span></div><div class="result-tags">${src.tags.map(t=>`<button class="result-tag" data-act="view" data-id="${t.passage_id}" style="border-left:3px solid ${themeColor(i)}" title="Deschide pasajul original"><strong>Trimitere ${esc(t.time?'· '+t.time:'· nedatat')} ↗</strong><span>${esc(t.excerpt)}</span></button>`).join('')}</div></div>`).join(''):`<div class="no-data">Nu s-au găsit rezultate pentru această formulare. Nu sunt generate trimiteri fictive.</div>`}
${group.has_more?`<div class="loadmore"><button class="btn block" data-act="load-more" data-group="${i}">Afișează următoarele trimiteri →</button></div>`:''}<div style="font-size:10px;color:#8596a7;padding:12px 19px;border-top:1px solid #eef2f7">${esc(group.warning)}</div></div></div>`).join('')}
function renderLab(){const notes=S.notes||[];let current=notes.find(x=>x.id===S.noteId);$('#main-content').innerHTML=`<div class="lab-layout"><aside class="panel"><div class="panel-heading"><h2>Proiectele tale</h2><button class="btn sm primary" data-act="new-note">＋ Nou</button></div><div class="panel-content"><p class="sm subtle">Organizează-ți singur analiza. Programul nu scrie concluzii în locul tău.</p><div class="note-list">${notes.length?notes.map(x=>`<button class="${x.id===S.noteId?'active':''}" data-act="choose-note" data-id="${x.id}"><strong>${esc(x.title)}</strong><div class="tiny subtle">${x.evidence.length} trimiteri · salvat local</div></button>`).join(''):'<div class="empty">Creează primul proiect.</div>'}</div></div></aside><section class="panel"><div class="panel-heading"><h2>Laboratorul istoricului</h2><span class="pill green">Sinteză proprie</span></div>${current?`<div class="editor-shell"><input id="note-title" class="editor-title" value="${esc(S.noteTitle)}" aria-label="Titlul sintezei" placeholder="Titlul cercetării…"><textarea id="note-body" class="editor-area" aria-label="Textul sintezei" placeholder="Scrie aici propria analiză, cronologie, ipoteze și concluzii. Sursele rămân atașate în panoul din dreapta.">${esc(S.noteBody)}</textarea><div class="editor-footer"><span class="sm subtle" id="autosave-status">Salvare automată activă. Datele rămân locale.</span><button class="btn primary" data-act="save-note">Salvează proiectul</button></div></div>`:'<div class="empty" style="margin:auto"><span class="glyph">✎</span><strong>Un spațiu pentru propriile tale concluzii.</strong><p>Alege „Nou” pentru a începe un proiect.</p><button class="btn primary" data-act="new-note">＋ Creează proiect</button></div>'}</section><aside class="panel"><div class="panel-heading"><h2>Dovezi atașate</h2><span class="pill">${current?current.evidence.length:0}</span></div><div class="panel-content">${current?.evidence?.length?current.evidence.map((x,i)=>`<div class="note-cite"><strong>[${i+1}] ${esc(x.source_title)} · ${esc(loc(x))}</strong><p>${esc(truncate(x.text,190))}</p><button class="text-button" data-act="view" data-id="${x.id}">Vezi în original ↗</button></div>`).join(''):'<div class="empty">Deschide o trimitere în Index sau Interogare și apasă „Adaugă în laborator”.</div>'}${current?`<button class="btn block" data-act="export-note">↓ Exportă sinteza (.md)</button>`:''}<div class="lab-tip"><strong>Rigoare documentară</strong><br>Textele citate sunt extrase din sursele atașate. Interpretările și sinteza aparțin exclusiv istoricului.</div></div></aside></div>`}
async function openViewer(pid){S.viewId=pid;const data=await api('/api/passages/'+pid);let p=data.passage;const isPdf=p.format==='.pdf';const isImage=['.png','.jpg','.jpeg'].includes(p.format);let body=(isPdf||isImage)?`<img src="/api/passages/${pid}/image" alt="Originalul paginii ${p.page} — citatul este evidențiat separat" onerror="this.insertAdjacentHTML('afterend','<p>Pagina nu poate fi redată.</p>');this.style.display='none'">`:`<div class="plainpage">${data.page_passages.map(x=>x.id===pid?`<mark style="background:#ffea9c">${esc(x.text)}</mark>`:esc(x.text)).join('\n\n')}</div>`;
$('#viewer').innerHTML=`<div class="viewer-dialog"><div class="viewer-top"><div><div class="caps">Vizualizator de surse · original</div><h2 id="viewer-title">${esc(p.source_title)} &nbsp; <span class="subtle">— ${esc(loc(p))}</span></h2></div><button class="iconbtn" data-act="close-view" aria-label="Închide vizualizatorul">✕</button></div><div class="viewer-grid"><div class="viewer-paper">${body}</div><aside class="viewer-inspector"><span class="caps">Pasajul indexat</span><h3>Trimitere verificabilă</h3><div class="excerpt-highlight">${esc(p.text)}</div><div class="viewer-citation"><strong>${esc(p.source_title)}</strong><br>${esc(loc(p))}${p.printed_label?' · pagină tipărită '+esc(p.printed_label):' · numerotare tipărită neverificată'} · ${p.time_literal?esc(p.time_literal)+' ('+esc(p.precision)+')':'Dată neprecizată'}</div>${isPdf?`<button class="btn sm" data-act="page-label" data-sid="${p.sid}" data-page="${p.page}" data-id="${p.id}" data-current="${esc(p.printed_label||'')}">✎ Numerotarea originală a paginii</button>`:''}<div class="section-title">Elemente atestate în pasaj</div><div class="overlap-tags">${data.entities.map(x=>`<span class="pill blue">${esc(x.name)}</span>`).join('')||'<span class="sm subtle">Niciun nume recunoscut automat.</span>'}</div><p class="right-hint">Pasaj extras din document; când este OCR, transcrierea este neverificată. Imaginea originală rămâne nemodificată; marcajul este în citatul din dreapta.</p><button class="btn block primary" data-act="attach-evidence" data-id="${p.id}">＋ Adaugă în laborator</button>
<div class="claim-form"><strong>Atestă relația explicită</strong><p class="right-hint">Alegi doar nume prezente în pasaj și copiezi predicatul literal. Nu este interpretare automată.</p>
<label>Subiect<select id="claim-subject">${data.entities.map(x=>`<option value="${x.id}">${esc(x.name)} (${esc(x.kind)})</option>`).join('')}</select></label>
<label>Formularea exactă a acțiunii / relației<input id="claim-predicate" placeholder="ex. a plecat în"/></label>
<label>Obiect / entitate (opțional)<select id="claim-object"><option value="">— nu este indicat —</option>${data.entities.map(x=>`<option value="${x.id}">${esc(x.name)}</option>`).join('')}</select></label>
<label>Context spațial explicit (opțional)<select id="claim-place"><option value="">— sursa nu-l precizează —</option>${data.entities.filter(x=>x.kind==='loc').map(x=>`<option value="${x.id}">${esc(x.name)}</option>`).join('')}</select></label>
<label>Temă definită de istoric (opțional)<input id="claim-theme" placeholder="ex. diplomație" /></label>
<button class="btn block" data-act="save-claim" data-id="${p.id}" ${data.entities.length?'':'disabled'}>✓ Salvează ca afirmație verificată</button></div></aside></div><div class="viewer-footer"><span class="sm subtle">Poziție: sursa ${p.sid}, ${esc(loc(p))}, pasajul ${p.seq+1}</span><div style="display:flex;gap:8px"><button class="btn" data-act="original" data-sid="${p.sid}" data-page="${p.page}" data-pdf="${isPdf?'1':'0'}">Deschide fișierul original ↗</button><button class="btn" data-act="close-view">Închide</button></div></div></div>`;$('#viewer').classList.remove('hidden');}
async function chooseEntity(id){id=Number(id);if(S.chosen.includes(id))S.chosen=S.chosen.filter(x=>x!==id);else if(S.chosen.length<12)S.chosen.push(id);else{toast('Poți selecta cel mult 12 elemente.');return}S.focus=S.chosen.includes(id)?id:S.chosen[0]||null;await loadDetail();renderIndex()}
async function forceIndex(){setBusy(true,'Am pornit procesarea. Poate dura pentru corpusuri mari.');try{
 await api('/api/index/start?'+params({ocr:S.ocrEnabled?1:0}),{method:'POST'});
 let data;
 for(let i=0;i<1800;i++){
   await new Promise(r=>setTimeout(r,1100));
   data=await api('/api/index/progress');
   if(data.job.status!=='running')break;
   if(i%4===0){const c=data.sources;toast(`Indexare în curs: ${c.indexed} indexate · ${c.pending} în așteptare`)}
 }
 if(data?.job.status==='error')throw new Error(data.job.error);
 if(data?.job.status==='running')throw new Error('Procesarea continuă în fundal. Revino pentru rezultate.');
 await Promise.all([refreshState(),loadEntities(),loadLayers(),loadClaims()]);await loadDetail();render();
 const errs=data?.job.result?.results?.filter(x=>x.status==='error')||[];
 toast(`Index completat. ${errs.length?'Fișiere cu eroare: '+errs.length:'Fișiere procesate.'}`);
 }catch(ex){err(ex)}finally{setBusy(false)}}
async function chooseTab(t){S.tab=t;render()}
async function doSearch(){let q=($('#main-query')?.value||S.query).trim();if(!q){toast('Scrie o întrebare sau expresie.');return}S.query=q;setBusy(true);try{S.results=await Promise.all([q,...S.themes].map(q=>api('/api/query?'+params({q,limit:500}))));renderSearch();toast('Trimiterile sunt din sursele efectiv indexate.')}catch(x){err(x)}finally{setBusy(false)}}
async function loadMore(groupIndex){
 let group=S.results?.[groupIndex];if(!group?.has_more)return;
 setBusy(true,'Se încarcă următoarele trimiteri…');
 try{
   const next=await api('/api/query?'+params({q:group.query,limit:500,offset:group.next_offset}));
   const byID=new Map(group.sources.map(x=>[x.source_id,x]));
   for(const src of next.sources){
     if(byID.has(src.source_id)){
       let existing=byID.get(src.source_id);
       existing.hits+=src.hits;existing.tags.push(...src.tags);
     }else{group.sources.push(src);byID.set(src.source_id,src)}
   }
   group.hits.push(...next.hits);
   group.total=next.total;group.has_more=next.has_more;group.next_offset=next.next_offset;
   renderSearch();
 }catch(ex){err(ex)}finally{setBusy(false)}
}
async function saveNote(){S.noteTitle=$('#note-title')?.value||S.noteTitle;S.noteBody=$('#note-body')?.value||S.noteBody;let result=await api('/api/notes',jsonOpts('POST',{id:S.noteId,title:S.noteTitle,body:S.noteBody}));S.noteId=result.id;await loadNotes();renderLab();toast('Proiectul a fost salvat local.')}
async function newNote(){let resp=await api('/api/notes',jsonOpts('POST',{title:'Cercetare nouă',body:''}));S.noteId=resp.id;await loadNotes();S.tab='lab';render();toast('Proiect creat. Scrie propria sinteză.')}
async function attachEvidence(id){if(!S.noteId){let r=await api('/api/notes',jsonOpts('POST',{title:'Dosar de cercetare',body:''}));S.noteId=r.id;}await api('/api/notes/'+S.noteId+'/evidence',jsonOpts('POST',{passage_id:Number(id)}));await loadNotes();toast('Pasaj atașat în laborator, fără duplicare.');}
async function changeYear(){S.yearActive=true;await Promise.all([loadLayers(),loadDetail(),loadClaims()]);renderIndex()}
async function openMetadata(sid){
 const d=await api('/api/sources/'+sid+'/metadata');
 const fields=[['title','Titlul bibliografic'],['author','Autor / editor'],['publication','Publicare / anul ediției'],['edition','Ediție / volum'],['archival_ref','Cotă arhivistică / referință'],['language','Limba sursei'],['remarks','Observații documentare']];
 $('#viewer').innerHTML=`<div class="viewer-dialog" style="width:min(660px,100%);height:auto;max-height:92vh"><div class="viewer-top"><div><div class="caps">Identificare bibliografică</div><h2 id="viewer-title">${esc(d.filename)}</h2></div><button class="iconbtn" data-act="close-view">×</button></div>
 <div class="metadata-form">${fields.map(([key,label])=>`<label>${label}<input data-meta-field="${key}" value="${esc(d[key]||'')}"></label>`).join('')}
 <p class="sm subtle">Pagina fizică a PDF-ului și numărul tipărit nu sunt presupuse identice. Ajustează numerele tipărite direct în cititor.</p></div>
 <div class="viewer-footer"><button class="btn" data-act="close-view">Anulează</button><button class="btn primary" data-act="save-metadata" data-id="${sid}">Salvează metadatele</button></div></div>`;
 $('#viewer').classList.remove('hidden');
}
async function saveMetadata(sid){
 const obj={}; document.querySelectorAll('[data-meta-field]').forEach(x=>obj[x.dataset.metaField]=x.value);
 await api('/api/sources/'+sid+'/metadata',jsonOpts('PUT',obj));
 $('#viewer').classList.add('hidden');
 await refreshState();render();toast('Fișa bibliografică a fost salvată.');
}
async function saveClaim(pid){
 const subject=Number($('#claim-subject')?.value||0);
 const predicate=($('#claim-predicate')?.value||'').trim();
 if(!subject||!predicate){toast('Alege subiectul și copiază formularea exactă a relației din pasaj.');return;}
 const v={passage_id:Number(pid),subject_id:subject,predicate,object_id:Number($('#claim-object')?.value||0)||null,place_id:Number($('#claim-place')?.value||0)||null,theme:$('#claim-theme')?.value||''};
 const r=await api('/api/claims',jsonOpts('POST',v));await loadClaims();await loadDetail();if(S.tab==='index')renderIndex();toast(r.deduplicated?'Atestare adăugată la afirmația existentă.':'Afirmație nouă verificată și legată de original.');
}
async function openClaimEvidence(id){let data=await api('/api/claims/'+id+'/evidence');const first=data.passages[0];if(!first)return toast('Atestarea nu mai este disponibilă.');const refs=data.passages.map((x,i)=>`${i+1}. ${x.source_title}, ${loc(x)}`).join('\n');if(data.passages.length>1)toast(`Afirmație atestată de ${data.passages.length} pasaje. Primul pasaj se deschide.`);await openViewer(first.id);}
async function onAction(b){let a=b.dataset.act;try{
 if(a==='tab')return chooseTab(b.dataset.tab);
 if(a==='load-more')return await loadMore(Number(b.dataset.group));
 if(a==='help')return alert('historytool — stație de lucru locală\n\nIndexare integrală a textului extras, deduplicare a afirmațiilor identice și trimiteri la pagini originale.\n\nAtenție: identificarea automată a entităților este parțială; coaparițiile nu sunt relații istorice; OCR este opțional, necesită instalarea Tesseract și verificare manuală. Nu promitem semantică exhaustivă sau absența tuturor erorilor.');
 if(a==='metadata')return await openMetadata(Number(b.dataset.id));
 if(a==='save-metadata')return await saveMetadata(Number(b.dataset.id));
 if(a==='page-label'){const label=prompt('Numărul TIPĂRIT pe această pagină (lasă gol dacă nu se vede):',b.dataset.current||'');if(label===null)return;await api('/api/sources/'+b.dataset.sid+'/pages/'+b.dataset.page+'/label',jsonOpts('PUT',{printed_label:label}));await openViewer(Number(b.dataset.id));toast('Eticheta paginii a fost salvată.');return}
 if(a==='backup'){openLocalFile('/api/backup');return}
 if(a==='verify'){const z=await api('/api/verify');const bad=z.sources.filter(x=>x.integrity!=='ok');alert(`${z.verified}/${z.total} surse verificate SHA-256. ${bad.length?bad.map(x=>x.title+' — '+x.integrity).join('\n'):'Toate fișierele existente sunt intacte.'}`);return}
 if(a==='audit'){const z=await api('/api/audit');alert(z.entries.slice(0,30).map(x=>x.created_at.slice(0,19)+' • '+x.action+' • '+x.subject).join('\n')||'Jurnal gol.');return}
 if(a==='delete-source'){if(!confirm(`Elimini ${b.dataset.name}? Se șterg și atestările sale. Creează întâi o copie de siguranță.`))return;await api('/api/sources/'+b.dataset.id,{method:'DELETE'});S.chosen=[];S.focus=null;await Promise.all([refreshState(),loadEntities(),loadLayers(),loadClaims()]);render();toast('Sursa a fost eliminată.');return}
 if(a==='new-entity'){const name=prompt('Nume sau termen exact pentru index:');if(!name?.trim())return;const kind=prompt('Tip: persoană, loc, instituție, eveniment, concept, obiect, candidat','candidat')||'candidat';await api('/api/entities',jsonOpts('POST',{name:name.trim(),kind:kind.trim()}));await Promise.all([loadEntities(),loadLayers()]);renderIndex();toast('Termenul a fost adăugat ca identitate candidată.');return}
 if(a==='claim-evidence')return await openClaimEvidence(Number(b.dataset.id));
 if(a==='save-claim')return await saveClaim(Number(b.dataset.id));
 if(a==='pick-files')return $('#upload-files').click();
 if(a==='demo'){setBusy(true);let x=await api('/api/demo',{method:'POST'});await refreshState();render();setBusy(false);return toast('Au fost încărcate texte FICTIVE demonstrative. Apasă „Indexează sursele”.')}
 if(a==='run-index')return await forceIndex();
 if(a==='mode'){S.indexMode=b.dataset.mode;await loadEntities();renderIndex();return}
 if(a==='select-entity')return await chooseEntity(b.dataset.id);
 if(a==='remove-selected'){S.chosen=S.chosen.filter(x=>x!==Number(b.dataset.id));S.focus=S.chosen[0]||null;await loadDetail();renderIndex();return}
 if(a==='level'){S.level=Number(b.dataset.level);renderIndex();return}
 if(a==='grain'){S.grain=b.dataset.grain;await Promise.all([loadLayers(),loadDetail()]);renderIndex();return}
 if(a==='year-active'){S.yearActive=!S.yearActive;await Promise.all([loadLayers(),loadDetail()]);renderIndex();return}
 if(a==='year-prev'||a==='year-next'){let direction=a==='year-next'?1:-1;let steps={'ere':1000,'epoci':250,'secole':100,'decenii':10,'ani':1};if(S.grain==='luni'){S.month+=direction;if(S.month>12){S.month=1;S.year++}if(S.month<1){S.month=12;S.year--}}else if(S.grain==='zile'){const daysInMonth=(y,m)=>{let leap=(y%4===0&&(y%100!==0||y%400===0));return [31,leap?29:28,31,30,31,30,31,31,30,31,30,31][m-1]};S.day+=direction;if(S.day>daysInMonth(S.year,S.month)){S.day=1;S.month++;if(S.month>12){S.month=1;S.year++}}if(S.day<1){S.month--;if(S.month<1){S.month=12;S.year--}S.day=daysInMonth(S.year,S.month)}}else S.year+=(steps[S.grain]||1)*direction;return await changeYear()}
 if(a==='view')return await openViewer(b.dataset.id);
 if(a==='close-view'){$('#viewer').classList.add('hidden');return}
 if(a==='original'){let url='/api/sources/'+b.dataset.sid+'/original'+(b.dataset.pdf==='1'?'#page='+b.dataset.page:'');openLocalFile(url);return}
 if(a==='search-submit')return await doSearch();
 if(a==='add-theme'){let value=prompt('Scrie tema paralelă (căutată independent și colorată distinct):');if(value?.trim()){if(S.themes.length>=5)return toast('Maximum 5 teme paralele.');S.themes.push(value.trim());S.results=null;renderSearch()}return}
 if(a==='remove-theme'){S.themes.splice(Number(b.dataset.num),1);S.results=null;renderSearch();return}
 if(a==='new-note')return await newNote();
 if(a==='choose-note'){S.noteId=Number(b.dataset.id);await loadNotes();renderLab();return}
 if(a==='save-note')return await saveNote();
 if(a==='export-note'){if(S.noteId)openLocalFile('/api/notes/'+S.noteId+'/export');return}
 if(a==='attach-evidence')return await attachEvidence(b.dataset.id);
 if(a==='confirm-entity'){await api('/api/entities/'+b.dataset.id,jsonOpts('PATCH',{status:'confirmat'}));await Promise.all([loadEntities(),loadDetail()]);renderIndex();return toast('Identitate confirmată prin decizia istoricului.')}
 if(a==='alias'){let al=prompt('Adaugă o formă de nume, numai dacă ai verificat că se referă la aceeași identitate:');if(al){await api('/api/entities/'+b.dataset.id+'/alias',jsonOpts('POST',{alias:al}));await Promise.all([loadEntities(),loadDetail(),loadLayers()]);renderIndex();toast('Alias salvat; aparițiile au fost reindexate.')}return}
 }catch(ex){err(ex);setBusy(false)}}
document.addEventListener('click',event=>{let b=event.target.closest('[data-act]');if(b){event.preventDefault();onAction(b)}});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!$('#viewer').classList.contains('hidden')){$('#viewer').classList.add('hidden')}if(event.key==='Enter'&&event.target.id==='main-query'){event.preventDefault();doSearch()}if(event.key==='Enter'&&event.target.id==='entity-filter'){event.preventDefault();S.entityFilter=event.target.value;loadEntities().then(renderIndex).catch(err)}});
document.addEventListener('change',async event=>{let t=event.target;try{
 if(t.id==='ocr-enable'){S.ocrEnabled=t.checked;}
 if(t.id==='upload-files'){let files=Array.from(t.files||[]);if(!files.length)return;setBusy(true,'Se încarcă '+files.length+' fișiere…');const form=new FormData();files.forEach(file=>form.append('files',file));let r=await api('/api/sources/upload',{method:'POST',body:form});t.value='';await refreshState();render();toast('Încărcate: '+r.files.filter(x=>!x.duplicate).length+' fișiere noi. Apasă „Indexează sursele”.');setBusy(false)}
 if(t.id==='year-input'){let n=Number(t.value);if(Number.isInteger(n)&&n>=-10000&&n<=2500){S.year=n;await changeYear()}else toast('Folosește un an între -10000 și 2500.')}
 if(t.id==='month-input'){S.month=Number(t.value);await changeYear()}
 if(t.id==='day-input'){let n=Number(t.value);if(Number.isInteger(n)&&n>=1&&n<=31){S.day=n;await changeYear()}else toast('Ziua trebuie să fie între 1 și 31.')}
 }catch(ex){err(ex);setBusy(false)}});
document.addEventListener('input',event=>{let t=event.target;if(t.id==='entity-filter'){S.entityFilter=t.value;window.clearTimeout(window.entityTimer);window.entityTimer=setTimeout(()=>{let active=document.activeElement===t;let pos=t.selectionStart;loadEntities().then(()=>{if(S.tab==='index'){let list=$('.index-list');if(list)list.innerHTML=renderIndexList()}}).catch(err)},260)}if(t.id==='main-query')S.query=t.value;if(t.id==='note-title'||t.id==='note-body'){
     if(t.id==='note-title')S.noteTitle=t.value;else S.noteBody=t.value;
     const status=$('#autosave-status');if(status)status.textContent='Modificări nesalvate…';
     clearTimeout(window.atlasNoteSaveTimer);
     window.atlasNoteSaveTimer=setTimeout(async()=>{
       if(!S.noteId||S.tab!=='lab')return;
       const id=S.noteId,title=S.noteTitle,body=S.noteBody;
       try{await api('/api/notes',jsonOpts('POST',{id,title,body}));if(S.noteId===id){const st=$('#autosave-status');if(st)st.textContent='✓ Salvat automat local.'}}
       catch(e){err(e)}
     },1300);
 }});
initial();
