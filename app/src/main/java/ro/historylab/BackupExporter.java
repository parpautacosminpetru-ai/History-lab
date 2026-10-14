package ro.historylab;

import android.content.ContentResolver;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.net.Uri;
import android.provider.BaseColumns;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.HashSet;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Export portabil, la cererea utilizatorului. Import/restaurare va veni într-o versiune ulterioară. */
public final class BackupExporter {
    private BackupExporter() { }

    public static void export(Context context,HistoryDb helper,Uri target) throws Exception {
        ContentResolver resolver=context.getContentResolver();
        try(OutputStream destination=resolver.openOutputStream(target)) {
            if(destination==null)throw new IOException("Destinație invalidă.");
            try(ZipOutputStream zip=new ZipOutputStream(destination)) {
                SQLiteDatabase db=helper.getReadableDatabase();
                JSONObject root=new JSONObject();root.put("schema_version",1);root.put("project","HistoryLab");
                root.put("note","Arhivă locală exportată explicit; sursele originale nu sunt modificate.");
                for(String table:HistoryDb.TABLES)root.put(table,dumpTable(db,table));
                byte[] bytes=root.toString(2).getBytes(java.nio.charset.StandardCharsets.UTF_8);
                zip.putNextEntry(new ZipEntry("manifest.json"));zip.write(bytes);zip.closeEntry();
                Set<String> seen=new HashSet<>();
                for(HistoryDb.Source s:helper.sources()) {
                    File f=new File(s.image);
                    if(!f.isFile())continue;
                    String name="originals/"+f.getName();
                    if(!seen.add(name))continue;
                    zip.putNextEntry(new ZipEntry(name));
                    try(FileInputStream in=new FileInputStream(f)) {
                        byte[] buffer=new byte[32768];int n;
                        while((n=in.read(buffer))!=-1)zip.write(buffer,0,n);
                    }
                    zip.closeEntry();
                }
            }
        }
    }

    private static JSONArray dumpTable(SQLiteDatabase db,String table) throws Exception {
        JSONArray rows=new JSONArray();
        try(Cursor c=db.query(table,null,null,null,null,null,null)) {
            while(c.moveToNext()) {
                JSONObject row=new JSONObject();
                for(int i=0;i<c.getColumnCount();i++) {
                    String name=c.getColumnName(i);
                    switch(c.getType(i)) {
                        case Cursor.FIELD_TYPE_NULL:row.put(name,JSONObject.NULL);break;
                        case Cursor.FIELD_TYPE_INTEGER:row.put(name,c.getLong(i));break;
                        case Cursor.FIELD_TYPE_FLOAT:row.put(name,c.getDouble(i));break;
                        case Cursor.FIELD_TYPE_STRING:row.put(name,c.getString(i));break;
                        default:throw new IOException("Tip de câmp neașteptat: "+name);
                    }
                }
                rows.put(row);
            }
        }
        return rows;
    }
}
