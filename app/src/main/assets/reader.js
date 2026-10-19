import {newId, uniqueTerms, historicalToAxis,
  findExistingPassage, putObjects} from "./model.js";
import {coverageReport, nextCandidate, indexPalette, appendChosenTag} from "./speed.js";

/**
 * Atlasul Explicit · atelier OCR offline.
 * Recunoașterea este exclusiv mecanică, prin biblioteca locală din Android.
 * Clasificarea semantică rămâne integral sub controlul utilizatorului.
 */
export function setupReader({getData, onDataChanged, notice, openSourceEditor, openEntry}) {
  const $ = id => document.getElementById(id);
  const panel = $("readerPanel");
  const native = () => window.HistoryOCRBridge;
  const contextIds=["readerSource","readerChapter","readerPageNumber"];
  const semantics=["readerTitle","readerTopics","readerIndexes","readerPeople","readerYear",
    "readerYearEnd","readerPlace","readerParagraph","readerSentence","readerLine","readerParaphrase"];
  let currentPageId=null;
  let pendingMetadata=null;
  let ocrTimer=null, savedRange=null, imageZoom=100, processing=false;
  let activePage=null;
  let segmentIndex=-1, lastAutoTitle="", lastManualTags=null, report=null;

  function pagePassages(){
    return !activePage ? [] : getData().passages.filter(p=>p.pageId===activePage.id);
  }

  function refreshCoverage() {
    report=coverageReport($("readerOcrText").value,pagePassages(),activePage?.id||"");
    const {total,indexed,percent,stale,unknown,candidates}=report;
    $("readerCoverageLabel").textContent="Acoperire textuală "+percent+"% · "+indexed+"/"+total+" caractere";
    $("readerCoverageBar").setAttribute("aria-valuenow",String(percent));
    $("readerCoverageFill").style.width=percent+"%";
    $("readerCoverageNote").textContent=stale
      ? stale+" selecții au poziții neconcordante după editarea textului; reverifică."
      : (unknown?"Citatele fără poziții OCR nu sunt contorizate.":
        "Acoperire de caractere, NU exhaustivitate semantică");
    if(segmentIndex>=candidates.length)segmentIndex=-1;
    $("readerSegmentCounter").textContent=(segmentIndex<0?0:segmentIndex+1)+" / "+candidates.length;
    for(const id of ["readerSegmentPrev","readerSegmentNext","readerNextUncovered"])
      $(id).disabled=!activePage||!$("readerOcrText").value.trim();
  }

  function restoreAutoNext(){
    try {
      const setting=localStorage.getItem("historylab-auto-next");
      if(setting!==null)$("readerAutoNext").checked=setting==="true";
    }catch(_){}
  }

  function loadRange(start,end,{autoTitle=true}={}) {
    const fullText=$("readerOcrText").value;
    if(!activePage||start<0||end<=start||end>fullText.length){
      notice("Nu există o selecție validă în text.");return false;
    }
    const quote=fullText.slice(start,end);
    if(!quote.trim()){notice("Selecția nu conține text.");return false;}
    const currentTitle=$("readerTitle").value.trim();
    const title=quote.trim().replace(/\s+/g," ").slice(0,110);
    savedRange={start,end,quote};
    $("readerQuote").value=quote;
    if(autoTitle&&(!currentTitle||currentTitle===lastAutoTitle))
      $("readerTitle").value=title;
    lastAutoTitle=title;
    const candidates=report?.candidates||[];
    const i=candidates.findIndex(s=>s.start<=start&&s.end>=end);
    segmentIndex=i;
    $("readerSegmentCounter").textContent=(i<0?0:i+1)+" / "+candidates.length;
    return true;
  }

  function goSegment(direction=1, onlyUncovered=false, afterIndex=segmentIndex) {
    if(!activePage){notice("Alege o pagină originală.");return;}
    refreshCoverage();
    const segment=nextCandidate(report,afterIndex,direction,onlyUncovered);
    if(!segment){
      notice(onlyUncovered?"Nu există segmente mecanice neacoperite.":"Nu există text OCR pe această pagină.");
      return;
    }
    if(!loadRange(segment.start,segment.end))return;
    const area=$("readerOcrText");
    area.focus({preventScroll:true});
    area.setSelectionRange(segment.start,segment.end);
    $("readerQuote").scrollIntoView({behavior:"smooth",block:"nearest"});
    notice("Segment propus de punctuație; verifică delimitarea și alege tu indexurile.");
  }

  function renderPalette() {
    const opts=indexPalette(getData().entries);
    $("readerPalette").innerHTML=opts.length
      ? opts.map(({kind,name})=>'<button type="button" data-kind="'+kind+'" data-name="'+esc(name)+
          '"><span>'+ (kind==="topic"?"TEMĂ":"INDICE")+'</span>'+esc(name)+'</button>').join("")
      : '<span class="reader-palette-empty">După primele fișe, indicii aleși manual vor apărea aici.</span>';
    for(const el of $("readerPalette").querySelectorAll("button[data-name]")){
      el.onclick=()=>{
        const target=el.dataset.kind==="topic"?"readerTopics":"readerIndexes";
        $(target).value=appendChosenTag($(target).value,el.dataset.name);
        notice("Indice aplicat la alegerea ta.");
      };
    }
  }

  function reapplyLastTags(){
    if(!lastManualTags){notice("Nu există încă indici folosiți în sesiunea curentă.");return;}
    for(const [id,terms] of [["readerTopics",lastManualTags.topics],["readerIndexes",lastManualTags.indexes]]){
      for(const term of terms)$(id).value=appendChosenTag($(id).value,term);
    }
    notice("Indicii anteriori au fost aplicați la cererea ta. Verifică-i pentru acest fragment.");
  }

  function findPage(id) {return getData().pages.find(p=>p.id===id);}
  function esc(s){return String(s||"").replace(/[&<>"']/g,c=>({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
  function saveReaderContext() {
    try {localStorage.setItem("historylab-reader-context",JSON.stringify({
      sourceId:$("readerSource").value,chapter:$("readerChapter").value,page:$("readerPageNumber").value
    }));} catch(_){}
  }
  function restoreContext() {
    try {
      const value=JSON.parse(localStorage.getItem("historylab-reader-context")||"{}");
      if(value.sourceId&&getData().sources.some(s=>s.id===value.sourceId))
        $("readerSource").value=value.sourceId;
      if(value.chapter)$("readerChapter").value=value.chapter;
      if(value.page)$("readerPageNumber").value=value.page;
    } catch(_){}
  }
  function setSaveState(text){$("readerSaveState").textContent=text;}
  function show(){
    if(!getData().sources.length){
      notice("Înregistrează mai întâi lucrarea bibliografică.");openSourceEditor();return;
    }
    panel.classList.remove("hidden");
    renderSources();
    if(currentPageId&&findPage(currentPageId))openPage(currentPageId);
    else if($("readerSource").value){
      renderPages();
      $("readerStatus").textContent="Alege o pagină";
    }
    window.setTimeout(()=>$("readerPageNumber").focus(),80);
  }
  function hide(){
    flushOcr().catch(e=>notice("Salvare OCR: "+e.message));
    panel.classList.add("hidden");
  }
  function renderSources(){
    const previous=$("readerSource").value;
    $("readerSource").innerHTML='<option value="">— Lucrare —</option>'+
      getData().sources.map(s=>'<option value="'+esc(s.id)+'">'+esc(s.author?
        s.author+" — "+s.title:s.title)+'</option>').join("");
    if(getData().sources.some(s=>s.id===previous))$("readerSource").value=previous;
    else restoreContext();
    renderPages();
  }
  function renderPages(){
    const id=$("readerSource").value;
    const pages=getData().pages.filter(p=>p.sourceId===id)
      .sort((a,b)=>{const n=Number(a.pageNumber)-Number(b.pageNumber);
        return (Number.isFinite(n)?n:0)||(a.createdAt||"").localeCompare(b.createdAt||"");});
    $("readerPageList").innerHTML='<option value="">— Alege o pagină scanată —</option>'+
      pages.map(p=>'<option value="'+esc(p.id)+'">'+esc("p. "+p.pageNumber+
        (p.verified?" ✓":" · neverificată"))+'</option>').join("");
    if(currentPageId&&pages.some(p=>p.id===currentPageId))$("readerPageList").value=currentPageId;
    $("readerStatus").textContent=pages.length+" fotografii în lucrare";
  }
  function resetIndexFields(){
    for(const id of semantics)$(id).value="";
    $("readerType").value="afirmatie";
    $("readerQuote").value="";
    savedRange=null;
    segmentIndex=-1;
    lastAutoTitle="";
  }
  function emptyPageView(){
    currentPageId=null;activePage=null;imageZoom=100;
    $("readerPhoto").classList.add("hidden");
    $("readerPhoto").removeAttribute("src");
    $("readerPhotoPlaceholder").classList.remove("hidden");
    $("readerOcrText").value="";
    $("readerOcrText").disabled=true;
    $("readerVerified").checked=false;
    $("readerVerified").disabled=true;
    $("readerOcrCount").textContent="0 caractere";
    $("readerIndexedCount").textContent="0 fișe din această pagină";
    $("readerPageList").value="";
    $("readerPhotoScale").textContent="100%";
    resetIndexFields();
    setSaveState("Aștept fotografia");
    contextIds.forEach(id=>$(id).disabled=false);
    refreshCoverage();
    renderPalette();
    renderPages();
  }
  function openPage(id) {
    const p=findPage(id);
    if(!p){emptyPageView();return;}
    activePage=p;currentPageId=p.id;
    $("readerSource").value=p.sourceId;
    $("readerChapter").value=p.chapter||"";
    $("readerPageNumber").value=p.pageNumber||"";
    $("readerChapter").disabled=true;
    $("readerPageNumber").disabled=true;
    $("readerSource").disabled=false;
    $("readerPageList").value=p.id;
    $("readerOcrText").disabled=false;
    $("readerOcrText").value=p.ocrText||"";
    $("readerOcrCount").textContent=$("readerOcrText").value.length+" caractere";
    $("readerVerified").disabled=false;
    $("readerVerified").checked=Boolean(p.verified);
    $("readerStatus").textContent="p. "+p.pageNumber+(p.verified?" · verificată":" · OCR de verificat");
    $("readerPhoto").src=safePhotoUrl(p);
    $("readerPhoto").classList.remove("hidden");
    $("readerPhotoPlaceholder").classList.add("hidden");
    imageZoom=100;applyImageZoom();
    const linkedIds=new Set(getData().passages.filter(fragment=>fragment.pageId===p.id).map(x=>x.id));
    const cnt=getData().entries.filter(e=>e.passageIds?.some(id=>linkedIds.has(id))).length;
    $("readerIndexedCount").textContent=cnt+" fișe din această pagină";
    resetIndexFields();
    setSaveState(p.verified?"Transcriere verificată":"OCR neconfirmat · corectează înainte de citare");
    saveReaderContext();renderPages();
    $("readerPageList").value=p.id;
    refreshCoverage();renderPalette();
  }
  function safePhotoUrl(p) {
    if(typeof p.imageDataUri==="string"&&/^data:image\/(jpeg|png|webp);base64,/i.test(p.imageDataUri))return p.imageDataUri;
    if(typeof p.imageUrl==="string"&&p.imageUrl.startsWith("https://appassets.androidplatform.net/pages/"))return p.imageUrl;
    return "";
  }
  function applyImageZoom(){
    $("readerPhoto").style.width=imageZoom+"%";
    $("readerPhotoScale").textContent=imageZoom+"%";
  }
  async function flushOcr(){
    window.clearTimeout(ocrTimer);ocrTimer=null;
    const p=activePage;
    if(!p)return;
    await putObjects([{table:"pages",value:{...p}}]);
    setSaveState(p.verified?"Salvat · text verificat":"Salvat · text OCR de verificat");
  }
  function scheduleOcrSave(){
    if(!activePage)return;
    activePage.ocrText=$("readerOcrText").value;
    activePage.verified=false;
    $("readerVerified").checked=false;
    $("readerOcrCount").textContent=activePage.ocrText.length+" caractere";
    $("readerStatus").textContent="p. "+activePage.pageNumber+" · corectare OCR";
    $("readerQuote").value="";savedRange=null;segmentIndex=-1;
    refreshCoverage();
    setSaveState("Se salvează transcrierea…");
    window.clearTimeout(ocrTimer);
    ocrTimer=window.setTimeout(()=>flushOcr().catch(e=>notice(e.message)),450);
  }
  function loadSelectedText(){
    if(!activePage){notice("Fotografiază o pagină înainte să indexezi.");return;}
    const area=$("readerOcrText");
    if(!loadRange(area.selectionStart,area.selectionEnd))return;
    $("readerQuote").scrollIntoView({behavior:"smooth",block:"nearest"});
    notice("Fragmentul original a fost preluat fără transcriere. Tu alegi indexurile.");
  }
  function beginNewPage(next=false){
    const sourceId=$("readerSource").value || activePage?.sourceId || "";
    const chapter=$("readerChapter").value||activePage?.chapter||"";
    const prevPage=$("readerPageNumber").value||activePage?.pageNumber||"";
    flushOcr().catch(e=>notice(e.message));
    emptyPageView();
    $("readerSource").value=sourceId;
    $("readerChapter").value=chapter;
    if(next&&/^\d+$/.test(prevPage))$("readerPageNumber").value=String(Number(prevPage)+1);
    else $("readerPageNumber").value=next?"":prevPage;
    saveReaderContext();
    $("readerPageNumber").focus();
  }
  function frozenMetadata(){
    const sourceId=$("readerSource").value,chapter=$("readerChapter").value.trim(),
      pageNumber=$("readerPageNumber").value.trim();
    if(!getData().sources.some(s=>s.id===sourceId)){notice("Selectează sursa bibliografică.");return null;}
    if(!pageNumber){notice("Introdu numărul paginii înainte de fotografiere.");return null;}
    return {sourceId,chapter,pageNumber};
  }
  function browse(kind){
    if(processing){notice("Așteaptă recunoașterea paginii curente.");return;}
    if(activePage){notice("Pentru o fotografie nouă, apasă mai întâi «Pagina +1» sau alege altă pagină.");return;}
    pendingMetadata=frozenMetadata();
    if(!pendingMetadata)return;
    processing=true;
    setSaveState("Aștept fotografia…");
    try {
      if(native()?.chooseImage && kind==="gallery")native().chooseImage();
      else if(native()?.capturePhoto && kind==="camera")native().capturePhoto();
      else {
        const input=$("readerLocalPick");
        if(kind==="camera")input.setAttribute("capture","environment");
        else input.removeAttribute("capture");
        input.click();
      }
    }catch(error){processing=false;notice("Nu pot deschide camera/galeria: "+error.message);}
  }
  async function createPage(result){
    if(!pendingMetadata){processing=false;return;}
    if(!result||typeof result!=="object"){processing=false;notice("Fotografia nu a fost recepționată.");return;}
    const page={
      id:newId(),createdAt:new Date().toISOString(),sourceId:pendingMetadata.sourceId,
      chapter:pendingMetadata.chapter,pageNumber:pendingMetadata.pageNumber,
      imageUrl:result.imageUrl||"",imageDataUri:result.imageDataUri||"",
      mimeType:result.mimeType||"image/jpeg",
      rawOcrText:String(result.text||""),ocrText:String(result.text||""),
      verified:false,ocrEngine:result.engine||"neprecizat"
    };
    if(!page.imageUrl&&!page.imageDataUri){processing=false;notice("Fotografia nu poate fi păstrată.");return;}
    try{
      await putObjects([{table:"pages",value:page}]);
      await onDataChanged();
      openPage(page.id);
      const hasText=page.ocrText.trim().length>0;
      notice(hasText?"Fotografia și textul OCR au fost salvate. Verifică transcrierea.":
        "Fotografia a fost salvată. OCR fără rezultat; poți transcrie manual.");
    }catch(error){notice("Salvarea fotografiei a eșuat: "+error.message);}
    finally{processing=false;pendingMetadata=null;}
  }
  function errFromNative(msg){
    processing=false;pendingMetadata=null;
    setSaveState("Captură nereușită");
    notice("OCR/captură: "+msg);
  }
  window.HistoryOCR={
    onPageReady:payload=>{
      try{const parsed=JSON.parse(payload);createPage(parsed);}catch(e){errFromNative("Răspuns invalid: "+e.message);}
    },
    onError:errFromNative
  };
  async function localFile(event) {
    const f=event.target.files?.[0];event.target.value="";
    if(!f){processing=false;pendingMetadata=null;return;}
    if(!/^image\/(jpeg|png|webp)$/.test(f.type)){errFromNative("Folosește o fotografie JPEG, PNG sau WebP.");return;}
    try{
      const url=await new Promise((resolve,reject)=>{
        const reader=new FileReader();
        reader.onload=()=>resolve(String(reader.result));
        reader.onerror=()=>reject(reader.error);
        reader.readAsDataURL(f);
      });
      await createPage({imageDataUri:url,mimeType:f.type,text:"",
        engine:"manual — OCR disponibil în APK Android"});
      notice("Imaginea este disponibilă. OCR automat funcționează în APK Android.");
    }catch(error){errFromNative(error.message);}
  }
  async function verifyPage(checked){
    if(!activePage){$("readerVerified").checked=false;return;}
    if(checked&&!$("readerOcrText").value.trim()){
      $("readerVerified").checked=false;notice("Transcrierea paginii este goală.");return;
    }
    activePage.ocrText=$("readerOcrText").value;
    activePage.verified=checked;
    try{await flushOcr();$("readerStatus").textContent="p. "+activePage.pageNumber+
      (checked?" · verificată":" · neverificată");renderPages();refreshCoverage();}
    catch(e){notice("Nu am putut salva verificarea: "+e.message);}
  }
  function validHistoricalYear(raw) {
    if(raw==="")return null;
    const n=Number(raw);
    if(historicalToAxis(n)===null)return undefined;
    return n;
  }
  async function quickSave(event) {
    event.preventDefault();
    if(!activePage||!currentPageId){notice("Nicio pagină selectată.");return;}
    if(!$("readerVerified").checked||!activePage.verified){
      notice("Confirmă verificarea transcrierii pe fotografia originală.");return;
    }
    if(!savedRange?.quote){notice("Selectează un fragment înainte de salvare.");return;}
    // Selecția nu poate rămâne validă dacă textul a fost modificat între timp.
    const fullText=$("readerOcrText").value;
    if(fullText.slice(savedRange.start,savedRange.end)!==savedRange.quote){
      savedRange=null;$("readerQuote").value="";notice("Selecția s-a schimbat; selectează din nou.");return;
    }
    const title=$("readerTitle").value.trim();
    if(!title){notice("Introdu un nume de regăsire pentru indexare.");return;}
    const st=validHistoricalYear($("readerYear").value),en=validHistoricalYear($("readerYearEnd").value);
    if(st===undefined||en===undefined||(st!==null&&en!==null&&historicalToAxis(en)<historicalToAxis(st))){
      notice("Corectează intervalul cronologic. Anul 0 nu există.");return;
    }
    const p={
      sourceId:activePage.sourceId,chapter:activePage.chapter,pageStart:activePage.pageNumber,
      pageEnd:"",paragraph:$("readerParagraph").value.trim(),
      sentence:$("readerSentence").value.trim(),line:$("readerLine").value.trim(),
      quote:savedRange.quote,pageId:activePage.id,
      offsetStart:savedRange.start,offsetEnd:savedRange.end,
      textVerified:true,verificationMethod:"comparat manual cu fotografia"
    };
    const old=findExistingPassage(getData().passages,p);
    const passage=old||{...p,id:newId(),createdAt:new Date().toISOString()};
    const entry={
      id:newId(),createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),
      passageIds:[passage.id],title,type:$("readerType").value,
      place:$("readerPlace").value.trim(),people:$("readerPeople").value.trim(),
      topics:uniqueTerms($("readerTopics").value),indexes:uniqueTerms($("readerIndexes").value),
      paraphrase:$("readerParaphrase").value.trim(),
      yearStart:st,yearEnd:en,month:null,day:null,dateText:"",lat:null,lon:null,geometry:[]
    };
    const selectedStart=savedRange.start;
    const chosen={topics:[...entry.topics],indexes:[...entry.indexes]};
    const writes=[{table:"entries",value:entry}];
    if(!old)writes.unshift({table:"passages",value:passage});
    $("readerSaveQuick").disabled=true;
    try{
      await flushOcr();
      await putObjects(writes);
      await onDataChanged();
      // Nu pierdem cartea, capitolul, pagina și fotografia.
      const savedPageId=activePage.id;
      const linkedIds=new Set(getData().passages.filter(x=>x.pageId===savedPageId).map(x=>x.id));
      $("readerIndexedCount").textContent=getData().entries.filter(e=>
        e.passageIds?.some(pid=>linkedIds.has(pid))).length+" fișe din această pagină";
      lastManualTags=chosen;
      resetIndexFields();
      renderPalette();
      refreshCoverage();
      setSaveState("Indexare salvată · gata pentru fragmentul următor");
      if($("readerAutoNext").checked){
        const current=report.candidates.findIndex(seg=>seg.start<=selectedStart&&seg.end>selectedStart);
        const anyUncovered=report.candidates.some(seg=>!seg.complete);
        if(anyUncovered)goSegment(1,true,current);
        else notice("Toate caracterele paginii sunt acoperite textual. Verifică separat exhaustivitatea semantică.");
      } else {
        $("readerOcrText").focus();
        notice(old?"Fișă salvată; citatul existent a fost reutilizat.":"Fișă și citat salvate, fără repetarea sursei.");
      }
    }catch(e){notice("Nu am putut salva fișa: "+e.message);}
    finally{$("readerSaveQuick").disabled=false;}
  }
  function refresh(){
    renderSources();
    renderPalette();
    if(currentPageId&&findPage(currentPageId)){
      activePage=findPage(currentPageId);
      refreshCoverage();
    }else if(currentPageId)emptyPageView();
  }

  $("readerClose").onclick=hide;
  $("readerGallery").onclick=()=>browse("gallery");
  $("readerCamera").onclick=()=>browse("camera");
  $("readerNextPage").onclick=()=>beginNewPage(true);
  $("readerPageList").onchange=e=>{
    flushOcr().catch(err=>notice(err.message));
    if(e.target.value)openPage(e.target.value);
    else beginNewPage(false);
  };
  $("readerSource").onchange=()=>{
    if(activePage)flushOcr().catch(e=>notice(e.message));
    const chosen=$("readerSource").value;
    emptyPageView();$("readerSource").value=chosen;
    renderPages();saveReaderContext();
  };
  for(const id of ["readerChapter","readerPageNumber"])$(id).oninput=saveReaderContext;
  $("readerPhotoIn").onclick=()=>{imageZoom=Math.min(320,imageZoom+25);applyImageZoom();};
  $("readerPhotoOut").onclick=()=>{imageZoom=Math.max(75,imageZoom-25);applyImageZoom();};
  $("readerOcrText").oninput=scheduleOcrSave;
  $("readerVerified").onchange=e=>verifyPage(e.target.checked);
  $("readerSelect").onclick=loadSelectedText;
  $("readerSegmentPrev").onclick=()=>goSegment(-1);
  $("readerSegmentNext").onclick=()=>goSegment(1);
  $("readerNextUncovered").onclick=()=>goSegment(1,true);
  $("readerUseLastIndices").onclick=reapplyLastTags;
  $("readerAutoNext").onchange=event=>{
    try{localStorage.setItem("historylab-auto-next",String(event.target.checked));}catch(_){}
  };
  $("readerQuickForm").onsubmit=quickSave;
  $("readerLocalPick").onchange=localFile;
  ["readerOcrText"].forEach(id=>$(id).addEventListener("keydown",e=>{
    if((e.ctrlKey||e.metaKey)&&e.key==="Enter"){e.preventDefault();loadSelectedText();}
  }));
  $("readerQuickForm").addEventListener("keydown",e=>{
    if((e.ctrlKey||e.metaKey)&&e.key==="Enter"){
      e.preventDefault();$("readerQuickForm").requestSubmit();
    }else if(e.altKey&&e.key==="ArrowRight"){
      e.preventDefault();goSegment(1);
    }else if(e.altKey&&e.key==="ArrowLeft"){
      e.preventDefault();goSegment(-1);
    }
  });
  renderSources();restoreContext();
  restoreAutoNext();
  emptyPageView();
  return {show,hide,refresh,openPage(id){show();openPage(id);}};
}
