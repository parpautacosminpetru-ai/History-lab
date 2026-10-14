package ro.historylab;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.text.Html;

import com.googlecode.tesseract.android.TessBaseAPI;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** OCR optic local (Tesseract), fără AI generativ și fără rețea. Rezultatul rămâne neverificat. */
public final class OcrEngine {
    public static class Result {
        public final String text;
        public final int width,height,confidence;
        public final List<HistoryDb.OcrBox> boxes;
        Result(String text,int width,int height,int confidence,List<HistoryDb.OcrBox> boxes) {
            this.text=text==null?"":text;
            this.width=width;this.height=height;this.confidence=confidence;this.boxes=boxes;
        }
    }
    private OcrEngine() { }

    private static File dataRoot(Context ctx) { return new File(ctx.getFilesDir(),"tesseract"); }
    private static File tessdata(Context ctx) { return new File(dataRoot(ctx),"tessdata"); }

    public static void installBundledModels(Context ctx) throws IOException {
        File dest=tessdata(ctx);
        if (!dest.isDirectory() && !dest.mkdirs()) throw new IOException("Nu se poate crea directorul OCR.");
        String[] assets=ctx.getAssets().list("tessdata");
        if(assets==null)return;
        for(String name:assets) {
            if(!name.endsWith(".traineddata"))continue;
            File target=new File(dest,name);
            if(target.isFile() && target.length()>100_000)continue;
            File tmp=new File(dest,name+".tmp");
            try(InputStream input=ctx.getAssets().open("tessdata/"+name);
                FileOutputStream output=new FileOutputStream(tmp)) {
                byte[] b=new byte[32*1024];int n;
                while((n=input.read(b))!=-1)output.write(b,0,n);
            }
            if(target.exists()&&!target.delete())throw new IOException("Nu se poate actualiza modelul OCR.");
            if(!tmp.renameTo(target))throw new IOException("Nu se poate instala modelul OCR.");
        }
    }

    public static void importModel(Context ctx,String name,InputStream in) throws IOException {
        if(!name.matches("[a-zA-Z0-9_]+\\.traineddata"))throw new IOException("Selectează un fișier .traineddata cu nume simplu.");
        File dir=tessdata(ctx);if(!dir.exists()&&!dir.mkdirs())throw new IOException("Nu se poate crea directorul.");
        File target=new File(dir,name);File tmp=new File(dir,name+".tmp");
        try(FileOutputStream out=new FileOutputStream(tmp)) {
            byte[] buffer=new byte[32768];int n;
            while((n=in.read(buffer))!=-1)out.write(buffer,0,n);
        }
        if(tmp.length()<100_000) {tmp.delete();throw new IOException("Fișierul modelului pare incomplet.");}
        if(target.exists()&&!target.delete())throw new IOException("Modelul vechi nu poate fi înlocuit.");
        if(!tmp.renameTo(target))throw new IOException("Nu s-a putut importa modelul.");
    }

    public static String installedLanguages(Context ctx) {
        File[] files=tessdata(ctx).listFiles((dir,name)->name.endsWith(".traineddata"));
        if(files==null)return "(niciunul)";
        String[] languages=new String[files.length];
        for(int i=0;i<files.length;i++)languages[i]=files[i].getName().replace(".traineddata","");
        Arrays.sort(languages);
        return String.join(", ",languages);
    }

    public static Result recognize(Context ctx,File imageFile,String language) throws IOException {
        installBundledModels(ctx);
        if(language==null||!language.matches("[a-zA-Z0-9_]+(\\+[a-zA-Z0-9_]+)*"))
            throw new IOException("Codul limbii nu este valid (ex.: ron+eng).");
        for(String lang:language.split("\\+"))
            if(!new File(tessdata(ctx),lang+".traineddata").exists())
                throw new IOException("Model OCR lipsă: "+lang+". Importă-l în Setări.");
        BitmapFactory.Options probe=new BitmapFactory.Options();probe.inJustDecodeBounds=true;
        BitmapFactory.decodeFile(imageFile.getAbsolutePath(),probe);
        if(probe.outWidth<=0||probe.outHeight<=0)throw new IOException("Format de imagine nerecunoscut.");
        int sample=1;
        while(Math.max(probe.outWidth,probe.outHeight)/sample>3000)sample*=2;
        BitmapFactory.Options options=new BitmapFactory.Options();options.inSampleSize=sample;
        Bitmap bitmap=BitmapFactory.decodeFile(imageFile.getAbsolutePath(),options);
        if(bitmap==null)throw new IOException("Nu se poate deschide imaginea.");
        TessBaseAPI api=new TessBaseAPI();
        try {
            if(!api.init(dataRoot(ctx).getAbsolutePath(),language))
                throw new IOException("Tesseract nu a putut inițializa limbile: "+language);
            api.setImage(bitmap);
            String raw=api.getUTF8Text();
            int confidence=api.meanConfidence();
            String hocr=api.getHOCRText(0);
            return new Result(raw,bitmap.getWidth(),bitmap.getHeight(),confidence,extractBoxes(hocr));
        } finally {
            api.recycle();bitmap.recycle();
        }
    }

    private static final Pattern SPAN=Pattern.compile("<span\\b([^>]*)>(.*?)</span>",Pattern.CASE_INSENSITIVE|Pattern.DOTALL);
    private static final Pattern BBOX=Pattern.compile("\\bbbox\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)\\s+(\\d+)");
    private static final Pattern WORD=Pattern.compile("\\bocrx_word\\b");

    static List<HistoryDb.OcrBox> extractBoxes(String hocr) {
        List<HistoryDb.OcrBox> result=new ArrayList<>();
        if(hocr==null)return result;
        Matcher words=SPAN.matcher(hocr);
        while(words.find()) {
            String attributes=words.group(1);
            if(!WORD.matcher(attributes).find())continue;
            Matcher rect=BBOX.matcher(attributes);
            if(!rect.find())continue;
            String value=Html.fromHtml(words.group(2),Html.FROM_HTML_MODE_LEGACY).toString().trim();
            if(value.isEmpty())continue;
            try {
                result.add(new HistoryDb.OcrBox(value,Integer.parseInt(rect.group(1)),Integer.parseInt(rect.group(2)),Integer.parseInt(rect.group(3)),Integer.parseInt(rect.group(4))));
            } catch(NumberFormatException ignored) { /* geometrie OCR invalidă, nu o inventăm */ }
        }
        return result;
    }
}
