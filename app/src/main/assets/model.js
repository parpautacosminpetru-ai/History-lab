// HistoryLab · nucleul local, fara AI si fara server.
export const TABLES = ["sources", "passages", "entries", "relations", "pages"];
const DB_NAME = "historylab-explicit-v1";

export function newId() {
  return (typeof crypto !== "undefined" && crypto.randomUUID)
    ? crypto.randomUUID()
    : "hl-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
}

export function textKey(text = "") {
  return String(text).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

export function uniqueTerms(text = "") {
  const terms = Array.isArray(text) ? text : String(text).split(/[,;\n]+/);
  const seen = new Set();
  return terms.map(s => String(s).trim()).filter(s => {
    const key = textKey(s);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function historicalToAxis(year) {
  if (year === null || year === undefined || year === "") return null;
  const y = Number(year);
  if (!Number.isFinite(y) || !Number.isInteger(y) || y === 0) return null;
  return y < 0 ? y + 1 : y;
}

export function axisToHistorical(axis) {
  const y = Math.floor(axis);
  return y <= 0 ? y - 1 : y;
}

export function historicalYearLabel(year) {
  const y = Number(year);
  if (!Number.isFinite(y) || y === 0) return "dată necunoscută";
  return y < 0 ? Math.abs(y) + " î.Hr." : y + " d.Hr.";
}

export function dateLabel(entry) {
  const start = entry.yearStart == null ? null : Number(entry.yearStart);
  const end = entry.yearEnd == null ? null : Number(entry.yearEnd);
  if (start == null && end == null) return "Nedatat";
  const first = entry.dateText ? entry.dateText : historicalYearLabel(start ?? end);
  if (end == null || end === start) return first;
  return first + " — " + historicalYearLabel(end);
}

export function dateAxis(entry, end = false) {
  const y = end && entry.yearEnd != null ? entry.yearEnd : entry.yearStart;
  const base = historicalToAxis(y);
  if (base === null) return null;
  if ((end && entry.yearEnd != null) || !entry.month || !entry.day) return base;
  // Pozitionare vizuala; nu transforma calendarul istoric intr-o certitudine.
  return base + (Math.min(12, Math.max(1, Number(entry.month))) - 1) / 12
    + (Math.min(31, Math.max(1, Number(entry.day))) - 1) / 372;
}

export function matchesPeriod(entry, center, span, includeUndated = false) {
  const a = dateAxis(entry), b = dateAxis(entry, true);
  if (a === null) return includeUndated;
  const lo = center - span / 2, hi = center + span / 2;
  return a <= hi && (b == null ? a : b) >= lo;
}

export function passageFingerprint(p) {
  const locator = [p.sourceId, p.chapter, p.pageStart, p.pageEnd, p.paragraph,
    p.sentence, p.line].map(v => String(v ?? "").trim()).join("|");
  return locator + "|" + JSON.stringify(String(p.quote ?? ""));
}

export function findExistingPassage(passages, candidate) {
  const fingerprint = passageFingerprint(candidate);
  return passages.find(p => passageFingerprint(p) === fingerprint) || null;
}

export function entrySearchText(entry, data) {
  const passages = data.passages.filter(p => (entry.passageIds || []).includes(p.id));
  const sourceIds = new Set(passages.map(p => p.sourceId));
  const sources = data.sources.filter(s => sourceIds.has(s.id));
  return textKey([
    entry.title, entry.type, entry.place, entry.people, entry.topics?.join(" "),
    entry.indexes?.join(" "), entry.paraphrase, entry.dateText, dateLabel(entry),
    ...passages.flatMap(p => [p.quote, p.chapter, p.pageStart, p.pageEnd, p.paragraph, p.sentence]),
    ...sources.flatMap(s => [s.title, s.author, s.speciality, s.publication, s.bibliography])
  ].filter(Boolean).join(" "));
}

export function queryEntries(data, {search = "", type = "all", sourceId = "all",
  center = 500, span = 5000, timeOnly = false, includeUndated = false, sort = "time"} = {}) {
  const parts = textKey(search).split(/\s+/).filter(Boolean);
  const sources = new Map(data.passages.map(p => [p.id, p.sourceId]));
  const entries = data.entries.filter(e => {
    if (type !== "all" && e.type !== type) return false;
    if (sourceId !== "all" && !(e.passageIds || []).some(id => sources.get(id) === sourceId)) return false;
    if (timeOnly && !matchesPeriod(e, center, span, includeUndated)) return false;
    if (parts.length) {
      const haystack = entrySearchText(e, data);
      const words = haystack.split(/[^a-z0-9]+/i).filter(Boolean);
      if (!parts.every(part => part.length === 1 ? words.includes(part) : haystack.includes(part))) return false;
    }
    return true;
  });
  if (sort === "source") {
    const anchor = e => {
      const p = data.passages.find(x => x.id === e.passageIds?.[0]);
      const s = data.sources.find(x => x.id === p?.sourceId);
      return [textKey(s?.author), textKey(s?.title), Number(p?.pageStart || 0), Number(p?.paragraph || 0)];
    };
    entries.sort((a, b) => {
      const aa = anchor(a), bb = anchor(b);
      return aa[0].localeCompare(bb[0]) || aa[1].localeCompare(bb[1]) || aa[2] - bb[2] || aa[3] - bb[3];
    });
  } else {
    entries.sort((a, b) => (dateAxis(a) ?? Infinity) - (dateAxis(b) ?? Infinity)
      || a.title.localeCompare(b.title, "ro"));
  }
  return entries;
}

export function validateBackup(value) {
  if (!value || typeof value !== "object" || value.format !== "historylab-explicit-1") {
    throw new Error("Fișierul nu este o arhivă HistoryLab compatibilă.");
  }
  // Arhivele realizate înainte de atelierul OCR nu conțin "pages".
  if (value.pages === undefined) value.pages = [];
  for (const table of TABLES) {
    if (!Array.isArray(value[table])) throw new Error("Lipsește secțiunea " + table);
    const ids = new Set();
    for (const item of value[table]) {
      if (!item || typeof item.id !== "string" || !item.id || ids.has(item.id)) {
        throw new Error("Identificator lipsă sau repetat în " + table);
      }
      ids.add(item.id);
    }
  }
  const sources = new Set(value.sources.map(s => s.id));
  const pages = new Set(value.pages.map(p => p.id));
  if (value.pages.some(p => !sources.has(p.sourceId))) throw new Error("Pagină fără sursă bibliografică.");
  const passages = new Set(value.passages.map(p => p.id));
  const entries = new Set(value.entries.map(e => e.id));
  if (value.passages.some(p => !sources.has(p.sourceId) || (p.pageId && !pages.has(p.pageId))))
    throw new Error("Trimitere la sursă sau fotografie absentă.");
  if (value.entries.some(e => !Array.isArray(e.passageIds) || !e.passageIds.length
    || e.passageIds.some(id => !passages.has(id)))) throw new Error("Fișă fără dovadă validă.");
  if (value.relations.some(r => !entries.has(r.fromId) || !entries.has(r.toId)
    || !passages.has(r.passageId))) throw new Error("Relație fără dovezi valide.");
  return value;
}

let connection;
export function openDatabase() {
  if (connection) return connection;
  connection = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 2);
    req.onupgradeneeded = () => {
      for (const name of TABLES) {
        if (!req.result.objectStoreNames.contains(name)) req.result.createObjectStore(name, {keyPath: "id"});
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return connection;
}

function perform(db, names, mode, job) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(names, mode);
    let result;
    try { result = job(tx); } catch (err) { tx.abort(); reject(err); return; }
    tx.oncomplete = () => resolve(result);
    tx.onerror = () => reject(tx.error || new Error("Eroare de stocare."));
    tx.onabort = () => reject(tx.error || new Error("Tranzacție anulată."));
  });
}

export async function loadData() {
  const db = await openDatabase();
  const out = {};
  await Promise.all(TABLES.map(table => new Promise((resolve, reject) => {
    const tx = db.transaction(table, "readonly");
    const request = tx.objectStore(table).getAll();
    request.onsuccess = () => { out[table] = request.result; resolve(); };
    request.onerror = () => reject(request.error);
  })));
  return out;
}

export async function putObjects(items) {
  if (!items.length) return;
  const db = await openDatabase();
  const tables = [...new Set(items.map(x => x.table))];
  if (tables.some(t => !TABLES.includes(t))) throw new Error("Categorie necunoscută.");
  await perform(db, tables, "readwrite", tx => {
    for (const {table, value} of items) tx.objectStore(table).put(value);
  });
}

export async function removeObject(table, id) {
  if (!TABLES.includes(table)) throw new Error("Categorie necunoscută.");
  const db = await openDatabase();
  await perform(db, [table], "readwrite", tx => tx.objectStore(table).delete(id));
}

export async function replaceData(backup) {
  validateBackup(backup);
  const db = await openDatabase();
  await perform(db, TABLES, "readwrite", tx => {
    for (const table of TABLES) {
      const store = tx.objectStore(table);
      store.clear();
      for (const item of backup[table]) store.put(item);
    }
  });
}

export async function makeBackup() {
  const records = await loadData();
  // Imaginile originale se includ în arhivă pentru transferul între dispozitive.
  // Dacă o imagine lipsește, exportul e oprit, nu produce un backup aparent complet.
  const pages = [];
  for (const original of records.pages) {
    const page = {...original};
    if (!page.imageDataUri && page.imageUrl) {
      const response = await fetch(page.imageUrl);
      if (!response.ok) throw new Error("Nu pot arhiva fotografia paginii " + (page.pageNumber || "?"));
      const blob = await response.blob();
      page.imageDataUri = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
      });
    }
    pages.push(page);
  }
  return {format: "historylab-explicit-1", exportedAt: new Date().toISOString(),
    ...records, pages};
}
