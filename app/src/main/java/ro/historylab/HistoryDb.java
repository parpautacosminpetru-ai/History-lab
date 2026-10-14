package ro.historylab;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import java.util.ArrayList;
import java.util.List;

/** Datele sunt locale. Originalele sunt fișiere separate, niciodată suprascrise de OCR. */
public final class HistoryDb extends SQLiteOpenHelper {
    public static final String[] TABLES = { "sources", "ocr_boxes", "ocr_runs", "annotations", "rules", "sheets", "sheet_links", "audit_log" };

    public static class Source {
        public long id, createdAt;
        public String title="", kind="", author="", date="", place="", reference="", image="", sha256="";
        public String raw="", corrected="", language="";
        public int fragment, verified, ocrWidth, ocrHeight, confidence;
        public String searchable() {
            return title + "\n" + kind + "\n" + author + "\n" + date + "\n" + place + "\n"
                    + reference + "\n" + (verified==1 ? corrected : raw);
        }
    }
    public static class OcrBox {
        public String word;
        public int left, top, right, bottom;
        public OcrBox(String word, int l, int t, int r, int b) {
            this.word=word; left=l; top=t; right=r; bottom=b;
        }
    }
    public static class Annotation {
        public long id, sourceId;
        public String quote, comment, status;
        public Annotation(long id,long sourceId,String quote,String comment,String status) {
            this.id=id;this.sourceId=sourceId;this.quote=quote;this.comment=comment;this.status=status;
        }
    }
    public static class Rule {
        public long id;
        public String axis, label, term;
        public Rule(long id,String axis,String label,String term) {
            this.id=id;this.axis=axis;this.label=label;this.term=term;
        }
    }
    public static class Sheet {
        public long id;
        public String title, content;
        public Sheet(long id,String title,String content) {
            this.id=id;this.title=title;this.content=content;
        }
    }

    public static class Audit {
        public String action,before,after;
        public long when;
        Audit(String action,String before,String after,long when) {
            this.action=action;this.before=before;this.after=after;this.when=when;
        }
    }

    public HistoryDb(Context context) { super(context, "historylab.sqlite", null, 1); }

    @Override public void onConfigure(SQLiteDatabase db) { db.setForeignKeyConstraintsEnabled(true); }

    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE sources (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,kind TEXT NOT NULL DEFAULT '',author TEXT NOT NULL DEFAULT '',date_text TEXT NOT NULL DEFAULT '',place TEXT NOT NULL DEFAULT '',reference TEXT NOT NULL DEFAULT '',fragment INTEGER NOT NULL DEFAULT 0,verified INTEGER NOT NULL DEFAULT 0,image_path TEXT NOT NULL,sha256 TEXT NOT NULL,ocr_raw TEXT NOT NULL DEFAULT '',ocr_corrected TEXT NOT NULL DEFAULT '',ocr_lang TEXT NOT NULL DEFAULT '',ocr_width INTEGER NOT NULL DEFAULT 0,ocr_height INTEGER NOT NULL DEFAULT 0,ocr_confidence INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE ocr_boxes (id INTEGER PRIMARY KEY AUTOINCREMENT,source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,word TEXT NOT NULL,left_px INTEGER NOT NULL,top_px INTEGER NOT NULL,right_px INTEGER NOT NULL,bottom_px INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX boxes_source ON ocr_boxes(source_id)");
        db.execSQL("CREATE TABLE ocr_runs (id INTEGER PRIMARY KEY AUTOINCREMENT,source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,raw_text TEXT NOT NULL,lang TEXT NOT NULL,confidence INTEGER NOT NULL,created_at INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE annotations (id INTEGER PRIMARY KEY AUTOINCREMENT,source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,quote TEXT NOT NULL,comment TEXT NOT NULL,status TEXT NOT NULL,created_at INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE rules (id INTEGER PRIMARY KEY AUTOINCREMENT,axis TEXT NOT NULL,label TEXT NOT NULL,term TEXT NOT NULL)");
        db.execSQL("CREATE TABLE sheets (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,content TEXT NOT NULL,updated_at INTEGER NOT NULL)");
        db.execSQL("CREATE TABLE sheet_links (id INTEGER PRIMARY KEY AUTOINCREMENT,sheet_id INTEGER NOT NULL REFERENCES sheets(id) ON DELETE CASCADE,source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,UNIQUE(sheet_id,source_id))");
        db.execSQL("CREATE TABLE audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT,entity TEXT NOT NULL,entity_id INTEGER NOT NULL,action TEXT NOT NULL,before_text TEXT NOT NULL,after_text TEXT NOT NULL,created_at INTEGER NOT NULL)");
    }

    @Override public void onUpgrade(SQLiteDatabase db,int oldVersion,int newVersion) {
        throw new IllegalStateException("Este necesară o migrare explicită; datele nu vor fi șterse.");
    }

    public long addSource(Source source) {
        ContentValues values = new ContentValues();
        values.put("title",source.title);values.put("kind",source.kind);values.put("author",source.author);
        values.put("date_text",source.date);values.put("place",source.place);values.put("reference",source.reference);
        values.put("fragment",source.fragment);values.put("verified",0);values.put("image_path",source.image);
        values.put("sha256",source.sha256);values.put("created_at",System.currentTimeMillis());
        return getWritableDatabase().insertOrThrow("sources",null,values);
    }

    private void audit(String entity,long id,String action,String before,String after) {
        ContentValues v=new ContentValues();v.put("entity",entity);v.put("entity_id",id);v.put("action",action);
        v.put("before_text",before==null?"":before);v.put("after_text",after==null?"":after);
        v.put("created_at",System.currentTimeMillis());getWritableDatabase().insertOrThrow("audit_log",null,v);
    }
    private String metadata(Source s) {
        if(s==null)return "";
        return "Titlu: "+s.title+"\nTip: "+s.kind+"\nAutor: "+s.author+"\nDată: "+s.date+"\nLoc: "+s.place+"\nReferință: "+s.reference+"\nFragment: "+s.fragment;
    }
    public List<Audit> audits(String entity,long id) {
        List<Audit> audits=new ArrayList<>();
        try(Cursor c=getReadableDatabase().query("audit_log",null,"entity=? AND entity_id=?",new String[]{entity,""+id},null,null,"id DESC","15")) {
            while(c.moveToNext())audits.add(new Audit(col(c,"action"),col(c,"before_text"),col(c,"after_text"),c.getLong(c.getColumnIndexOrThrow("created_at"))));
        }
        return audits;
    }
    public void updateSource(Source s) {
        Source previous=source(s.id);
        ContentValues values = new ContentValues();
        values.put("title",s.title);values.put("kind",s.kind);values.put("author",s.author);
        values.put("date_text",s.date);values.put("place",s.place);values.put("reference",s.reference);
        values.put("fragment",s.fragment);
        getWritableDatabase().update("sources",values,"id=?",new String[]{""+s.id});
        audit("source",s.id,"Editare metadate",metadata(previous),metadata(s));
    }

    public void saveOcr(long sourceId,OcrEngine.Result ocr,String language) {
        SQLiteDatabase db=getWritableDatabase();
        db.beginTransaction();
        try {
            ContentValues history=new ContentValues();history.put("source_id",sourceId);history.put("raw_text",ocr.text);
            history.put("lang",language);history.put("confidence",ocr.confidence);history.put("created_at",System.currentTimeMillis());
            db.insertOrThrow("ocr_runs",null,history);
            ContentValues values=new ContentValues();
            values.put("ocr_raw",ocr.text);values.put("ocr_corrected","");values.put("verified",0);
            values.put("ocr_lang",language);values.put("ocr_width",ocr.width);
            values.put("ocr_height",ocr.height);values.put("ocr_confidence",ocr.confidence);
            db.update("sources",values,"id=?",new String[]{""+sourceId});
            db.delete("ocr_boxes","source_id=?",new String[]{""+sourceId});
            for(OcrBox box:ocr.boxes) {
                ContentValues b=new ContentValues();b.put("source_id",sourceId);b.put("word",box.word);
                b.put("left_px",box.left);b.put("top_px",box.top);
                b.put("right_px",box.right);b.put("bottom_px",box.bottom);
                db.insertOrThrow("ocr_boxes",null,b);
            }
            audit("source",sourceId,"Rulare OCR ("+language+")","",ocr.text);
            db.setTransactionSuccessful();
        } finally { db.endTransaction(); }
    }

    public void verifyOcr(long id,String checked) {
        Source previous=source(id);
        ContentValues values=new ContentValues();values.put("ocr_corrected",checked);values.put("verified",1);
        getWritableDatabase().update("sources",values,"id=?",new String[]{""+id});
        audit("source",id,"Revizuire transcriere",previous==null?"":(previous.verified==1?previous.corrected:previous.raw),checked);
    }

    private Source fromCursor(Cursor c) {
        Source s=new Source();
        s.id=c.getLong(c.getColumnIndexOrThrow("id"));
        s.title=col(c,"title");s.kind=col(c,"kind");s.author=col(c,"author");
        s.date=col(c,"date_text");s.place=col(c,"place");s.reference=col(c,"reference");
        s.image=col(c,"image_path");s.sha256=col(c,"sha256");s.raw=col(c,"ocr_raw");
        s.corrected=col(c,"ocr_corrected");s.language=col(c,"ocr_lang");
        s.fragment=c.getInt(c.getColumnIndexOrThrow("fragment"));
        s.verified=c.getInt(c.getColumnIndexOrThrow("verified"));
        s.ocrWidth=c.getInt(c.getColumnIndexOrThrow("ocr_width"));
        s.ocrHeight=c.getInt(c.getColumnIndexOrThrow("ocr_height"));
        s.confidence=c.getInt(c.getColumnIndexOrThrow("ocr_confidence"));
        s.createdAt=c.getLong(c.getColumnIndexOrThrow("created_at"));
        return s;
    }
    private static String col(Cursor c,String name) { String s=c.getString(c.getColumnIndexOrThrow(name));return s==null?"":s; }

    public Source source(long id) {
        try(Cursor c=getReadableDatabase().query("sources",null,"id=?",new String[]{""+id},null,null,null)) {
            return c.moveToFirst()?fromCursor(c):null;
        }
    }
    public List<Source> sources() {
        List<Source> items=new ArrayList<>();
        try(Cursor c=getReadableDatabase().query("sources",null,null,null,null,null,"created_at DESC,id DESC")) {
            while(c.moveToNext())items.add(fromCursor(c));
        }
        return items;
    }
    public List<OcrBox> boxes(long sourceId) {
        List<OcrBox> items=new ArrayList<>();
        try(Cursor c=getReadableDatabase().query("ocr_boxes",null,"source_id=?",new String[]{""+sourceId},null,null,"id")) {
            while(c.moveToNext())items.add(new OcrBox(col(c,"word"),c.getInt(c.getColumnIndexOrThrow("left_px")),c.getInt(c.getColumnIndexOrThrow("top_px")),c.getInt(c.getColumnIndexOrThrow("right_px")),c.getInt(c.getColumnIndexOrThrow("bottom_px"))));
        }
        return items;
    }
    public long addAnnotation(long sourceId,String quote,String comment,String status) {
        ContentValues v=new ContentValues();v.put("source_id",sourceId);v.put("quote",quote);
        v.put("comment",comment);v.put("status",status);v.put("created_at",System.currentTimeMillis());
        return getWritableDatabase().insertOrThrow("annotations",null,v);
    }
    public List<Annotation> annotations(long sourceId) {
        List<Annotation> items=new ArrayList<>();
        try(Cursor c=getReadableDatabase().query("annotations",null,"source_id=?",new String[]{""+sourceId},null,null,"id DESC")) {
            while(c.moveToNext())items.add(new Annotation(c.getLong(c.getColumnIndexOrThrow("id")),sourceId,col(c,"quote"),col(c,"comment"),col(c,"status")));
        }
        return items;
    }
    public void addRule(String axis,String label,String term) {
        ContentValues v=new ContentValues();v.put("axis",axis);v.put("label",label);v.put("term",term);
        getWritableDatabase().insertOrThrow("rules",null,v);
    }
    public void deleteRule(long id) { getWritableDatabase().delete("rules","id=?",new String[]{""+id}); }
    public List<Rule> rules() {
        List<Rule> items=new ArrayList<>();
        try(Cursor c=getReadableDatabase().query("rules",null,null,null,null,null,"axis,label,id")) {
            while(c.moveToNext())items.add(new Rule(c.getLong(c.getColumnIndexOrThrow("id")),col(c,"axis"),col(c,"label"),col(c,"term")));
        }
        return items;
    }
    public long saveSheet(long id,String title,String content) {
        Sheet previous=id==0?null:sheet(id);
        ContentValues v=new ContentValues();v.put("title",title);v.put("content",content);v.put("updated_at",System.currentTimeMillis());
        if(id==0) {
            long newId=getWritableDatabase().insertOrThrow("sheets",null,v);
            audit("sheet",newId,"Fișă creată","",title+"\n"+content);return newId;
        }
        getWritableDatabase().update("sheets",v,"id=?",new String[]{""+id});
        audit("sheet",id,"Revizuire fișă",previous==null?"":previous.title+"\n"+previous.content,title+"\n"+content);
        return id;
    }
    public Sheet sheet(long id) {
        try(Cursor c=getReadableDatabase().query("sheets",null,"id=?",new String[]{""+id},null,null,null)) {
            return c.moveToFirst()?new Sheet(id,col(c,"title"),col(c,"content")):null;
        }
    }
    public List<Sheet> sheets() {
        List<Sheet> items=new ArrayList<>();
        try(Cursor c=getReadableDatabase().query("sheets",null,null,null,null,null,"updated_at DESC,id DESC")) {
            while(c.moveToNext())items.add(new Sheet(c.getLong(c.getColumnIndexOrThrow("id")),col(c,"title"),col(c,"content")));
        }
        return items;
    }
    public List<Long> sheetSources(long sheetId) {
        List<Long> ids=new ArrayList<>();
        try(Cursor c=getReadableDatabase().query("sheet_links",new String[]{"source_id"},"sheet_id=?",new String[]{""+sheetId},null,null,"id")) {
            while(c.moveToNext())ids.add(c.getLong(0));
        }
        return ids;
    }
    public void replaceSheetLinks(long sheetId,List<Long> ids) {
        SQLiteDatabase db=getWritableDatabase();db.beginTransaction();
        try {
            db.delete("sheet_links","sheet_id=?",new String[]{""+sheetId});
            for(long sourceId:ids) {
                ContentValues v=new ContentValues();v.put("sheet_id",sheetId);v.put("source_id",sourceId);
                db.insertOrThrow("sheet_links",null,v);
            }
            db.setTransactionSuccessful();
        } finally { db.endTransaction(); }
    }
}
