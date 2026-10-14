package ro.historylab;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.HorizontalScrollView;
import android.graphics.Color;
import android.graphics.drawable.Drawable;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** HistoryLab: atelier personal, offline. Nicio funcție nu scrie interpretări în locul istoricului. */
public final class MainActivity extends Activity {
    private static final int TAKE_PHOTO=101, PICK_IMAGE=102, PICK_MODEL=103, EXPORT_BACKUP=104, EXPORT_SHEET=105;
    // Paletă inspirată de hârtia de arhivă, cerneala tipografică și legăturile de piele.
    private static final int INK=0xFF192F38, MUTED=0xFF68736D, PAPER=0xFFF6F1E8,
        ACCENT=0xFF24635B, EDGE=0xFFE0D8CB, GOLD=0xFFBD955B, WHITE=0xFFFFFDFA,
        SAND=0xFFF0E9DC, DANGER=0xFF9A653B;
    private HistoryDb db;
    private LinearLayout content;
    private String currentTab="Atelier",lastSearch="",sourceFilter="Toate";
    private File pendingCamera;
    private long pendingSheetExport=0;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        db=new HistoryDb(this);
        if(savedInstanceState!=null) {
            String path=savedInstanceState.getString("pending_camera");
            if(path!=null)pendingCamera=new File(path);
            currentTab=savedInstanceState.getString("tab","Atelier");
            sourceFilter=savedInstanceState.getString("filter","Toate");
            lastSearch=savedInstanceState.getString("search","");
        }
        getWindow().setStatusBarColor(INK);
        getWindow().setNavigationBarColor(PAPER);
        renderTab(currentTab);
    }

    @Override protected void onSaveInstanceState(Bundle bundle) {
        super.onSaveInstanceState(bundle);
        if(pendingCamera!=null)bundle.putString("pending_camera",pendingCamera.getAbsolutePath());
        bundle.putString("tab",currentTab);bundle.putString("search",lastSearch);bundle.putString("filter",sourceFilter);
    }

    @Override protected void onDestroy() {
        if(db!=null)db.close();
        super.onDestroy();
    }

    private int dp(float pixels) {return Math.round(pixels*getResources().getDisplayMetrics().density);}
    private LinearLayout col() {LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);return l;}
    private LinearLayout row() {LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.HORIZONTAL);l.setGravity(Gravity.CENTER_VERTICAL);return l;}
    private void pad(View v,int a,int b,int c,int d) {v.setPadding(dp(a),dp(b),dp(c),dp(d));}
    private GradientDrawable bg(int color,int radius,int border) {
        GradientDrawable b=new GradientDrawable();b.setColor(color);b.setCornerRadius(dp(radius));
        if(border!=0)b.setStroke(dp(1),border);
        return b;
    }
    private GradientDrawable gradient(int begin,int end,int radius) {
        GradientDrawable b=new GradientDrawable(GradientDrawable.Orientation.TL_BR,new int[]{begin,end});
        b.setCornerRadius(dp(radius));return b;
    }
    private TextView txt(String value,int sp,int color,boolean bold) {
        TextView v=new TextView(this);v.setText(value);v.setTextSize(sp);v.setTextColor(color);
        if(bold)v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);
        v.setLineSpacing(dp(2),1f);return v;
    }
    private TextView serif(String value,int sp,int color) {
        TextView v=txt(value,sp,color,false);v.setTypeface(Typeface.create("serif",Typeface.BOLD));
        v.setLetterSpacing(-0.018f);return v;
    }
    private View spacer(int h) {View v=new View(this);v.setLayoutParams(new LinearLayout.LayoutParams(1,dp(h)));return v;}
    private TextView button(String title,Runnable action,boolean primary) {
        TextView b=txt(title,14,primary?Color.WHITE:INK,true);
        b.setGravity(Gravity.CENTER);pad(b,14,13,14,13);b.setMinHeight(dp(48));
        b.setBackground(bg(primary?ACCENT:WHITE,13,primary?0:EDGE));
        b.setContentDescription(title);b.setOnClickListener(v->action.run());return b;
    }
    private void buttonFull(LinearLayout parent,String title,Runnable action,boolean primary) {
        TextView b=button(title,action,primary);
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.bottomMargin=dp(9);parent.addView(b,p);
    }
    private void heading(LinearLayout parent,String heading,String sub) {
        TextView label=txt("ATELIER DE ISTORIE",10,ACCENT,true);label.setLetterSpacing(0.17f);parent.addView(label);
        parent.addView(spacer(6));parent.addView(serif(heading,28,INK));
        if(sub!=null&&!sub.isEmpty()) {parent.addView(spacer(7));parent.addView(txt(sub,13,MUTED,false));}
        parent.addView(spacer(18));
    }
    private LinearLayout panel(LinearLayout parent) {
        LinearLayout c=col();pad(c,17,17,17,17);c.setBackground(bg(WHITE,17,EDGE));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.bottomMargin=dp(12);
        parent.addView(c,lp);return c;
    }
    private void section(LinearLayout parent,String overline,String heading) {
        parent.addView(spacer(13));
        TextView small=txt(overline,10,ACCENT,true);small.setLetterSpacing(0.14f);parent.addView(small);
        parent.addView(spacer(5));parent.addView(serif(heading,21,INK));parent.addView(spacer(12));
    }
    private TextView pill(String title,boolean selected,Runnable action) {
        TextView t=txt(title,12,selected?Color.WHITE:INK,selected);t.setGravity(Gravity.CENTER);
        pad(t,13,10,13,10);t.setMinHeight(dp(42));
        t.setBackground(bg(selected?ACCENT:WHITE,24,selected?0:EDGE));
        t.setContentDescription(title);if(action!=null)t.setOnClickListener(v->action.run());return t;
    }
    private EditText field(LinearLayout root,String label,String value,boolean multi) {
        TextView t=txt(label,12,INK,true);
        LinearLayout.LayoutParams labelParams=new LinearLayout.LayoutParams(-1,-2);
        labelParams.topMargin=dp(10);root.addView(t,labelParams);
        EditText e=new EditText(this);e.setText(value);e.setTextSize(15);e.setTextColor(INK);
        e.setSingleLine(!multi);
        if(multi){e.setMinLines(5);e.setGravity(Gravity.TOP|Gravity.START);}
        e.setBackground(bg(WHITE,10,EDGE));pad(e,12,11,12,11);e.setMinHeight(dp(48));
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.topMargin=dp(5);
        root.addView(e,p);return e;
    }
    private ScrollView dialogScroll(LinearLayout form) {
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(false);pad(scroll,16,0,16,0);
        scroll.addView(form);return scroll;
    }
    private String value(EditText edit) {return edit.getText().toString().trim();}
    private void toast(String t) {Toast.makeText(this,t,Toast.LENGTH_LONG).show();}
    private void copyText(String text) {
        ClipboardManager clipboard=(ClipboardManager)getSystemService(Context.CLIPBOARD_SERVICE);
        if(clipboard!=null){clipboard.setPrimaryClip(ClipData.newPlainText("HistoryLab",text));toast("Copiat");}
    }
    private void showError(Exception e) {toast("Eroare: "+e.getMessage());}

    private void chrome(String active) {
        currentTab=active;
        LinearLayout root=col();root.setBackgroundColor(PAPER);
        root.setOnApplyWindowInsetsListener((v,insets)->{
            v.setPadding(0,insets.getSystemWindowInsetTop(),0,insets.getSystemWindowInsetBottom());
            return insets;
        });
        LinearLayout header=col();header.setBackgroundColor(INK);pad(header,19,13,19,15);
        LinearLayout identity=row();
        TextView seal=serif("H",21,GOLD);seal.setGravity(Gravity.CENTER);
        seal.setBackground(bg(0xFF27414A,13,0xFF6D644F));
        identity.addView(seal,new LinearLayout.LayoutParams(dp(43),dp(43)));
        LinearLayout names=col();pad(names,11,0,0,0);
        names.addView(serif("HistoryLab",25,Color.WHITE));
        TextView caption=txt("ATELIERUL ISTORICULUI",10,0xFFE6CDA6,true);
        caption.setLetterSpacing(0.16f);names.addView(caption);
        identity.addView(names,new LinearLayout.LayoutParams(0,-2,1));
        TextView settings=txt("⚙",23,0xFFE9D8C0,false);settings.setGravity(Gravity.CENTER);
        settings.setContentDescription("Setările atelierului");
        settings.setOnClickListener(v->renderTab("Setări"));
        identity.addView(settings,new LinearLayout.LayoutParams(dp(46),dp(48)));
        header.addView(identity);header.addView(spacer(11));
        LinearLayout status=row();
        TextView offline=txt("●  OFFLINE",10,0xFFAEE1CB,true);
        offline.setLetterSpacing(0.10f);status.addView(offline);
        TextView promise=txt("    •    ORIGINALUL RĂMÂNE INTACT",10,0xFFE2D9CC,false);
        status.addView(promise);header.addView(status);root.addView(header);

        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);
        scroll.setVerticalScrollBarEnabled(false);
        content=col();pad(content,16,20,16,28);scroll.addView(content);
        root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));

        LinearLayout nav=row();nav.setBackground(bg(WHITE,0,EDGE));pad(nav,5,7,5,7);
        String[] tabs={"Atelier","Surse","Căutare","Index","Fișe"};
        String[] icons={"⌂","▤","⌕","⌗","✎"};
        for(int i=0;i<tabs.length;i++) {
            String tab=tabs[i];boolean chosen=tab.equals(active);
            LinearLayout item=col();item.setGravity(Gravity.CENTER);pad(item,1,4,1,4);
            if(chosen)item.setBackground(bg(0xFFEAF0EB,12,0));
            TextView icon=txt(icons[i],23,chosen?ACCENT:MUTED,false);
            icon.setGravity(Gravity.CENTER);item.addView(icon);
            TextView label=txt(tab,10,chosen?ACCENT:MUTED,chosen);
            label.setGravity(Gravity.CENTER);item.addView(label);
            item.setContentDescription("Deschide "+tab);item.setOnClickListener(v->renderTab(tab));
            nav.addView(item,new LinearLayout.LayoutParams(0,dp(55),1));
        }
        root.addView(nav);setContentView(root);
    }
    private void renderTab(String tab) {
        chrome(tab);
        switch(tab) {
            case "Atelier":atelierPage();break;
            case "Surse":sourcesPage();break;
            case "Index":indexPage();break;
            case "Căutare":searchPage();break;
            case "Fișe":sheetsPage();break;
            default:settingsPage();break;
        }
    }

    private void stat(LinearLayout stats,String count,String label) {
        LinearLayout block=col();block.setGravity(Gravity.CENTER);
        block.addView(serif(count,26,INK));block.addView(spacer(3));
        TextView caption=txt(label,11,MUTED,false);caption.setGravity(Gravity.CENTER);block.addView(caption);
        stats.addView(block,new LinearLayout.LayoutParams(0,dp(72),1));
    }
    private void toolCard(LinearLayout parent,String symbol,String name,String hint,Runnable action) {
        LinearLayout card=col();pad(card,15,16,13,14);card.setBackground(bg(WHITE,16,EDGE));
        TextView glyph=txt(symbol,22,GOLD,true);card.addView(glyph);card.addView(spacer(7));
        card.addView(txt(name,14,INK,true));card.addView(spacer(3));
        card.addView(txt(hint,11,MUTED,false));card.setOnClickListener(v->action.run());
        card.setContentDescription(name+". "+hint);
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,dp(137),1);
        lp.setMargins(dp(0),0,dp(5),dp(10));parent.addView(card,lp);
    }
    private void atelierPage() {
        List<HistoryDb.Source> sources=db.sources();
        List<HistoryDb.Sheet> sheets=db.sheets();
        int pending=0;for(HistoryDb.Source s:sources)if(s.verified!=1)pending++;
        LinearLayout hero=col();pad(hero,21,23,21,21);
        hero.setBackground(gradient(0xFF162D37,0xFF2A514A,23));
        LinearLayout.LayoutParams hp=new LinearLayout.LayoutParams(-1,-2);hp.bottomMargin=dp(15);
        content.addView(hero,hp);
        TextView eyebrow=txt("✦  SPAȚIUL TĂU DE CERCETARE",10,0xFFECCB94,true);
        eyebrow.setLetterSpacing(0.14f);hero.addView(eyebrow);hero.addView(spacer(13));
        hero.addView(serif("Istoria începe cu o sursă.",28,Color.WHITE));
        hero.addView(spacer(9));
        hero.addView(txt("Arhivează originalul. Verifică textul. Construiește propriile interpretări.",13,0xFFE1EBE3,false));
        hero.addView(spacer(17));
        buttonFull(hero,"＋  Fotografiază o sursă",this::launchCamera,true);
        TextView importButton=button("Importă o imagine din telefon  ↗",this::launchImagePicker,false);
        hero.addView(importButton,new LinearLayout.LayoutParams(-1,-2));

        LinearLayout stats=col();stats.setBackground(bg(WHITE,17,EDGE));pad(stats,9,13,9,10);
        LinearLayout numbers=row();stat(numbers,""+sources.size(),"Surse");stat(numbers,""+pending,"De verificat");
        stat(numbers,""+sheets.size(),"Fișe proprii");stats.addView(numbers);
        LinearLayout.LayoutParams sp=new LinearLayout.LayoutParams(-1,-2);sp.bottomMargin=dp(10);content.addView(stats,sp);
        section(content,"INSTRUMENTE DE LUCRU","Masa de cercetare");
        LinearLayout first=row();content.addView(first);
        toolCard(first,"▤","Arhiva","Fotografii & originale",()->renderTab("Surse"));
        toolCard(first,"⌕","Căutare","Pasaje și trimiteri",()->renderTab("Căutare"));
        LinearLayout second=row();content.addView(second);
        toolCard(second,"⌗","Index tematic","Axe și intersecții",()->renderTab("Index"));
        toolCard(second,"◷","Cronologie","Date introduse de tine",this::timelinePage);
        LinearLayout third=row();content.addView(third);
        toolCard(third,"✎","Fișe de sinteză","Marginalii & argumente",()->renderTab("Fișe"));
        toolCard(third,"◇","Arhivă de siguranță","Export local",()->renderTab("Setări"));

        section(content,"PE MASA DE LUCRU","Ultimele surse");
        if(sources.isEmpty()){
            LinearLayout empty=panel(content);
            empty.addView(serif("Arhiva te așteaptă",19,INK));empty.addView(spacer(7));
            empty.addView(txt("Fotografiază sau importă prima pagină. Imaginea originală va rămâne distinctă de OCR și de notele tale.",13,MUTED,false));
        } else {
            for(int i=0;i<Math.min(2,sources.size());i++)sourceCard(content,sources.get(i),"");
            buttonFull(content,"Vezi întreaga arhivă  →",()->renderTab("Surse"),false);
        }
        if(!sheets.isEmpty()){
            section(content,"REDACTARE PERSONALĂ","Fișe în lucru");
            for(int i=0;i<Math.min(2,sheets.size());i++){
                HistoryDb.Sheet s=sheets.get(i);LinearLayout panel=panel(content);
                panel.addView(txt("✎  "+s.title,15,INK,true));panel.addView(spacer(4));
                panel.addView(txt(db.sheetSources(s.id).size()+" trimiteri la surse",12,ACCENT,false));
                panel.setOnClickListener(v->sheetPage(s.id));
            }
        }
        content.addView(spacer(10));
        TextView principle=txt("✦  Nicio concluzie automată. Fiecare interpretare îți aparține.",12,MUTED,false);
        principle.setGravity(Gravity.CENTER);pad(principle,5,9,5,15);content.addView(principle);
    }

    private void timelinePage() {
        chrome("Atelier");
        buttonFull(content,"← Înapoi la atelier",()->renderTab("Atelier"),false);
        heading(content,"Cronologia surselor","Afișează numai datele introduse de cercetător. Nu deduce evenimente sau datări.");
        List<HistoryDb.Source> dated=new ArrayList<>(),other=new ArrayList<>();
        for(HistoryDb.Source s:db.sources()){
            if(TimelineOrder.leadingYear(s.date)>=0)dated.add(s);else other.add(s);
        }
        java.util.Collections.sort(dated,(a,b)->{
            int year=Integer.compare(TimelineOrder.leadingYear(a.date),TimelineOrder.leadingYear(b.date));
            return year!=0?year:a.date.compareToIgnoreCase(b.date);
        });
        if(dated.isEmpty() && other.isEmpty()){
            LinearLayout empty=panel(content);empty.addView(serif("Nicio sursă introdusă",18,INK));
            empty.addView(txt("Adaugă o sursă și completează data sau perioada cunoscută.",13,MUTED,false));
            buttonFull(empty,"Adaugă prima sursă",this::pickSource,true);
            return;
        }
        content.addView(txt("ORDONARE DUPĂ PRIMUL AN NUMERIC SCRIS",10,ACCENT,true));
        content.addView(spacer(11));
        for(HistoryDb.Source s:dated){
            LinearLayout line=row();line.setGravity(Gravity.TOP);
            LinearLayout rail=col();rail.setGravity(Gravity.CENTER_HORIZONTAL);pad(rail,0,10,6,0);
            TextView point=txt("●",18,GOLD,true);rail.addView(point);
            line.addView(rail,new LinearLayout.LayoutParams(dp(29),-1));
            LinearLayout card=col();pad(card,16,14,16,14);
            card.setBackground(bg(WHITE,16,EDGE));
            LinearLayout.LayoutParams cardParams=new LinearLayout.LayoutParams(0,-2,1);
            cardParams.bottomMargin=dp(11);line.addView(card,cardParams);
            card.addView(serif(s.date,18,INK));card.addView(spacer(5));
            card.addView(txt(s.title,14,INK,true));
            card.addView(spacer(3));card.addView(txt(s.place.isEmpty()?"Data indicată de istoric":s.place,12,MUTED,false));
            card.setContentDescription("Sursă datată "+s.date+": "+s.title);
            card.setOnClickListener(v->detailPage(s.id,""));
            content.addView(line);
        }
        if(!other.isEmpty()){
            section(content,"FĂRĂ AN NUMERIC INIȚIAL","Datări neuniforme");
            content.addView(txt("Nu atribuim automat ani acestor surse. Păstrăm exact data introdusă.",12,MUTED,false));
            content.addView(spacer(10));
            for(HistoryDb.Source s:other)sourceCard(content,s,"");
        }
    }

    // === ARHIVA SURSELOR ===
    private void sourcesPage() {
        heading(content,"Arhiva surselor","Originalele rămân păstrate local. Transcrierile și interpretările sunt separate.");
        buttonFull(content,"＋  Fotografiază / importă document",this::pickSource,true);
        HorizontalScrollView chooser=new HorizontalScrollView(this);chooser.setHorizontalScrollBarEnabled(false);
        LinearLayout filters=row();pad(filters,0,1,0,9);chooser.addView(filters);
        String[] filterOptions={"Toate","De verificat","Verificate","Fragmente"};
        for(String option:filterOptions){
            TextView chip=pill(option,sourceFilter.equals(option),()->{
                sourceFilter=option;renderTab("Surse");
            });
            LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-2,-2);params.rightMargin=dp(7);
            filters.addView(chip,params);
        }
        content.addView(chooser);content.addView(spacer(9));
        List<HistoryDb.Source> all=db.sources(),filtered=new ArrayList<>();
        for(HistoryDb.Source s:all){
            if("Verificate".equals(sourceFilter)&&s.verified!=1)continue;
            if("De verificat".equals(sourceFilter)&&s.verified==1)continue;
            if("Fragmente".equals(sourceFilter)&&s.fragment!=1)continue;
            filtered.add(s);
        }
        content.addView(txt(filtered.size()+" din "+all.size()+" surse",12,MUTED,false));content.addView(spacer(12));
        if(filtered.isEmpty()){
            LinearLayout empty=panel(content);
            empty.addView(serif(all.isEmpty()?"Arhiva ta începe aici":"Nicio sursă în acest filtru",18,INK));
            empty.addView(spacer(7));empty.addView(txt(all.isEmpty()?"Fotografiază sau importă un document și completează metadatele.":"Selectează alt filtru pentru a vedea documentele.",13,MUTED,false));
        }
        for(HistoryDb.Source s:filtered)sourceCard(content,s,"");
    }
    private Bitmap thumbnail(String path) {
        BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;
        BitmapFactory.decodeFile(path,bounds);
        int sample=1;while(Math.max(bounds.outWidth,bounds.outHeight)/sample>380)sample*=2;
        BitmapFactory.Options opts=new BitmapFactory.Options();opts.inSampleSize=sample;
        return BitmapFactory.decodeFile(path,opts);
    }
    private void sourceCard(LinearLayout parent,HistoryDb.Source s,String marker) {
        LinearLayout card=panel(parent);LinearLayout inner=row();inner.setGravity(Gravity.TOP|Gravity.CENTER_VERTICAL);
        ImageView image=new ImageView(this);image.setScaleType(ImageView.ScaleType.CENTER_CROP);
        image.setBackground(bg(SAND,11,0));image.setClipToOutline(true);
        Bitmap thumb=thumbnail(s.image);if(thumb!=null)image.setImageBitmap(thumb);
        LinearLayout.LayoutParams ip=new LinearLayout.LayoutParams(dp(81),dp(103));ip.rightMargin=dp(13);
        inner.addView(image,ip);
        LinearLayout info=col();info.addView(txt(s.kind.isEmpty()?"DOCUMENT DE ARHIVĂ":s.kind.toUpperCase(Locale.ROOT),10,ACCENT,true));
        info.addView(spacer(5));info.addView(serif(s.title,17,INK));info.addView(spacer(6));
        String meta=(s.date.isEmpty()?"Dată nespecificată":s.date)+(s.place.isEmpty()?"":"  ·  "+s.place);
        info.addView(txt(meta,12,MUTED,false));info.addView(spacer(8));
        String status=s.raw.isEmpty()?"OCR de efectuat":s.verified==1?"Text verificat":"OCR neverificat";
        TextView state=txt((s.fragment==1?"FRAGMENT  ·  ":"")+status,11,s.verified==1?ACCENT:DANGER,true);
        info.addView(state);inner.addView(info,new LinearLayout.LayoutParams(0,-2,1));
        card.addView(inner);
        card.setContentDescription("Deschide sursa: "+s.title+", "+status);
        card.setOnClickListener(v->detailPage(s.id,marker));
    }
    private void pickSource() {
        new AlertDialog.Builder(this).setTitle("Adaugă sursă")
            .setItems(new String[]{"Fotografiază cu camera","Importă imagine existentă"},(d,which)->{
                if(which==0)launchCamera();else launchImagePicker();
            }).show();
    }
    private void launchImagePicker() {
        Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("image/*");startActivityForResult(intent,PICK_IMAGE);
    }
    private void launchCamera() {
        try {
            File folder=new File(getCacheDir(),"captures");if(!folder.isDirectory()&&!folder.mkdirs())throw new Exception("Camera cache");
            pendingCamera=new File(folder,"photo-"+UUID.randomUUID()+".jpg");
            Uri uri=FileProvider.getUriForFile(this,getPackageName()+".fileprovider",pendingCamera);
            Intent intent=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            intent.putExtra(MediaStore.EXTRA_OUTPUT,uri);
            intent.setClipData(ClipData.newRawUri("HistoryLab photo",uri));
            intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);
            if(intent.resolveActivity(getPackageManager())==null){toast("Nu există o aplicație de cameră.");return;}
            startActivityForResult(intent,TAKE_PHOTO);
        } catch(Exception e){showError(e);}
    }
    private static class Original {
        String path,sha;
        Original(String path,String sha){this.path=path;this.sha=sha;}
    }
    private Original preserveOriginal(Uri uri) throws Exception {
        File dir=new File(getFilesDir(),"originals");
        if(!dir.isDirectory()&&!dir.mkdirs())throw new Exception("Nu se poate crea arhiva locală.");
        File dest=new File(dir,UUID.randomUUID()+".img");
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        long bytes=0;
        try(InputStream input=getContentResolver().openInputStream(uri);
            OutputStream output=new FileOutputStream(dest)) {
            if(input==null)throw new Exception("Imaginea nu poate fi citită.");
            byte[] buffer=new byte[32768];int n;
            while((n=input.read(buffer))!=-1){output.write(buffer,0,n);digest.update(buffer,0,n);bytes+=n;}
        } catch(Exception e){dest.delete();throw e;}
        if(bytes==0){dest.delete();throw new Exception("Imaginea este goală.");}
        // Datele sursei originale rămân octet cu octet identice.
        StringBuilder sha=new StringBuilder();for(byte b:digest.digest())sha.append(String.format(Locale.ROOT,"%02x",b&0xff));
        return new Original(dest.getAbsolutePath(),sha.toString());
    }
    private void sourceMetadataDialog(Uri uri) {
        LinearLayout form=col();
        form.addView(txt("Datele sunt completate de istoric, nu ghicite de aplicație.",13,MUTED,false));
        EditText title=field(form,"Titlu (opțional; altfel se atribuie un ID tehnic)","",false);
        EditText kind=field(form,"Tip (primară, secundară, manuscris etc.)","",false);
        EditText author=field(form,"Autor / creator, dacă este cunoscut","",false);
        EditText date=field(form,"Dată / perioadă, exact cum o cunoști","",false);
        EditText place=field(form,"Localitate / loc asociat","",false);
        EditText ref=field(form,"Arhivă, fond, cotă, pagină sau proveniență","",false);
        CheckBox fragment=new CheckBox(this);fragment.setText("Sursa este fragmentară / incompletă");form.addView(fragment);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Fișa sursei noi").setView(dialogScroll(form))
            .setNegativeButton("Anulează",null).setPositiveButton("Salvează + OCR",null).create();
        dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            try {
                Original o=preserveOriginal(uri);
                HistoryDb.Source s=new HistoryDb.Source();
                s.title=value(title).isEmpty()?"Sursă locală "+new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm",Locale.ROOT).format(new java.util.Date()):value(title);s.kind=value(kind);
                s.author=value(author);s.date=value(date);s.place=value(place);s.reference=value(ref);
                s.fragment=fragment.isChecked()?1:0;s.image=o.path;s.sha256=o.sha;
                long id;
                try{id=db.addSource(s);}catch(Exception error){new File(o.path).delete();throw error;}
                dialog.dismiss();
                if(pendingCamera!=null && uri.getScheme()!=null && uri.getScheme().equals("file")) {
                    pendingCamera.delete();pendingCamera=null;
                }
                detailPage(id,"");
                toast("Original arhivat. OCR pornește automat.");
                performOcr(id,"ron+eng");
            }catch(Exception e){showError(e);}
        }));
        dialog.show();
    }

    private void editSourceDialog(HistoryDb.Source s) {
        LinearLayout form=col();
        EditText title=field(form,"Titlu",s.title,false);
        EditText kind=field(form,"Tip",s.kind,false);
        EditText author=field(form,"Autor",s.author,false);
        EditText date=field(form,"Dată",s.date,false);
        EditText place=field(form,"Localitate",s.place,false);
        EditText ref=field(form,"Referință arhivistică / proveniență",s.reference,false);
        CheckBox fragment=new CheckBox(this);fragment.setText("Sursă fragmentară");fragment.setChecked(s.fragment==1);form.addView(fragment);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Corectează metadatele")
            .setView(dialogScroll(form)).setNegativeButton("Renunță",null).setPositiveButton("Salvează",null).create();
        dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            if(value(title).isEmpty()){title.setError("Obligatoriu");return;}
            s.title=value(title);s.kind=value(kind);s.author=value(author);s.date=value(date);
            s.place=value(place);s.reference=value(ref);s.fragment=fragment.isChecked()?1:0;
            db.updateSource(s);dialog.dismiss();detailPage(s.id,"");
        }));dialog.show();
    }

    private Bitmap decodePreview(String path) {
        BitmapFactory.Options probe=new BitmapFactory.Options();probe.inJustDecodeBounds=true;
        BitmapFactory.decodeFile(path,probe);
        int sample=1;while(Math.max(probe.outWidth,probe.outHeight)/sample>2500)sample*=2;
        BitmapFactory.Options options=new BitmapFactory.Options();options.inSampleSize=sample;
        return BitmapFactory.decodeFile(path,options);
    }

    private void detailPage(long id,String highlight) {
        HistoryDb.Source s=db.source(id);if(s==null){renderTab("Surse");return;}
        chrome("Surse");
        buttonFull(content,"← Înapoi la arhivă",()->renderTab("Surse"),false);
        heading(content,s.title,"Document original + transcriere + fișă de lucru");
        LinearLayout meta=panel(content);
        meta.addView(txt("DATE FURNIZATE DE ISTORIC",11,ACCENT,true));meta.addView(spacer(7));
        meta.addView(txt("Tip: "+blank(s.kind)+"\nAutor: "+blank(s.author)+"\nDată: "+blank(s.date)
                +"\nLocalitate: "+blank(s.place)+"\nProveniență: "+blank(s.reference),14,INK,false));
        meta.addView(spacer(6));meta.addView(txt("SHA-256 original: "+s.sha256,11,MUTED,false));
        if(s.fragment==1)meta.addView(txt("Fragment / sursă incompletă",12,0xFF95672C,true));
        meta.addView(spacer(10));buttonFull(meta,"Editează metadatele",()->editSourceDialog(s),false);
        buttonFull(meta,"Vezi jurnalul documentului",()->auditDialog("source",s.id),false);
        content.addView(txt("ORIGINAL • mărește imaginea cu două degete",11,ACCENT,true));
        content.addView(spacer(7));
        ZoomImageView zoom=new ZoomImageView(this);
        try {
            Bitmap b=decodePreview(s.image);
            if(b!=null)zoom.setContent(b,db.boxes(s.id),s.ocrWidth,s.ocrHeight,highlight);
        }catch(Exception e){toast("Imagine indisponibilă: "+e.getMessage());}
        content.addView(zoom,new LinearLayout.LayoutParams(-1,dp(350)));
        content.addView(spacer(12));
        if(!s.raw.isEmpty())buttonFull(content,"Marchează o expresie pe imagine",()->highlightDialog(s.id),false);
        LinearLayout transcription=panel(content);
        transcription.addView(txt("TRANSCRIERE OCR • rezultat mecanic",12,ACCENT,true));
        transcription.addView(spacer(6));
        if(s.raw.isEmpty()) {
            transcription.addView(txt("Nu există încă OCR. Fotografia originală rămâne disponibilă.",14,MUTED,false));
        } else {
            transcription.addView(txt("Limbi: "+s.language+"  •  scor optic estimativ: "+s.confidence
                    +"%  •  "+(s.verified==1?"verificat de istoric":"NEVERIFICAT"),12,MUTED,false));
            transcription.addView(spacer(7));
            TextView raw=txt(s.raw,14,INK,false);raw.setTextIsSelectable(true);
            transcription.addView(raw);transcription.addView(spacer(12));
            buttonFull(transcription,"Copiază textul OCR brut",()->copyText(s.raw),false);
            if(s.verified==1) {
                transcription.addView(spacer(8));transcription.addView(txt("VERSIUNEA REVIZUITĂ DE ISTORIC",12,ACCENT,true));
                transcription.addView(spacer(5));
                TextView checked=txt(s.corrected,14,INK,false);checked.setTextIsSelectable(true);
                transcription.addView(checked);
            }
            buttonFull(transcription,"Verifică / corectează transcrierea",()->editTranscription(s),true);
        }
        buttonFull(transcription,"Rulează OCR pe această fotografie",()->requestOcr(s),s.raw.isEmpty());
        LinearLayout citations=panel(content);
        citations.addView(txt("TRIMITERE LA SURSĂ",12,ACCENT,true));citations.addView(spacer(6));
        String cite=CitationFormatter.format(s.author,s.title,s.date,s.reference);
        citations.addView(txt(cite,14,INK,false));citations.addView(spacer(7));
        citations.addView(txt("Șablon bibliografic orientativ; verifică normele Chicago sau cerințele instituției.",12,MUTED,false));
        buttonFull(citations,"Copiază referința",()->copyText(cite),false);
        LinearLayout notes=panel(content);
        notes.addView(txt("MARGINALII & ÎNTREBĂRI • semnate de cercetător",12,ACCENT,true));
        notes.addView(spacer(9));buttonFull(notes,"+ Adaugă citat / întrebare / comentariu",()->annotationDialog(s.id),true);
        List<HistoryDb.Annotation> annotations=db.annotations(s.id);
        if(annotations.isEmpty())notes.addView(txt("Nicio însemnare încă.",13,MUTED,false));
        for(HistoryDb.Annotation a:annotations) {
            notes.addView(spacer(10));notes.addView(txt(a.status,11,0xFF95672C,true));
            if(!a.quote.trim().isEmpty())notes.addView(txt("„"+a.quote+"”",14,INK,false));
            notes.addView(txt(a.comment,14,MUTED,false));
        }
    }
    private String blank(String s){return s==null||s.isEmpty()?"—":s;}

    private void editTranscription(HistoryDb.Source s) {
        LinearLayout form=col();form.addView(txt("Textul OCR brut nu se modifică. Salvezi o versiune corectată distinctă, asumată de tine.",13,MUTED,false));
        EditText text=field(form,"Transcriere revizuită",s.verified==1?s.corrected:s.raw,true);
        text.setMinLines(11);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Verificare paleografică / filologică")
            .setView(dialogScroll(form)).setNegativeButton("Anulează",null)
            .setPositiveButton("Confirm transcrierea",(d,w)->{
                db.verifyOcr(s.id,text.getText().toString());detailPage(s.id,"");
            }).create();dialog.show();
    }
    private void requestOcr(HistoryDb.Source s) {
        EditText lang=new EditText(this);lang.setSingleLine(true);lang.setText(s.language.isEmpty()?"ron+eng":s.language);
        String message="Recunoaștere optică locală. Nu există interpretare sau traducere automată."
                +"\n\nLimbi disponibile: "+OcrEngine.installedLanguages(this)
                +(s.raw.isEmpty()?"":"\n\nO nouă rulare se păstrează în istoricul OCR; versiunea verificată curentă va fi resetată.");
        new AlertDialog.Builder(this).setTitle("Extrage OCR")
            .setMessage(message).setView(lang).setNegativeButton("Anulează",null)
            .setPositiveButton("Extrage",(d,w)->performOcr(s.id,value(lang))).show();
    }
    private void performOcr(long sourceId,String lang) {
        toast("OCR în lucru pe dispozitiv. Pentru fotografii mari poate dura.");
        new Thread(()->{
            try {
                HistoryDb.Source current=db.source(sourceId);
                if(current==null)throw new Exception("Sursa nu mai există.");
                OcrEngine.Result result=OcrEngine.recognize(getApplicationContext(),new File(current.image),lang);
                db.saveOcr(sourceId,result,lang);
                runOnUiThread(()->{
                    toast("OCR încheiat; textul necesită verificare.");
                    if(currentTab.equals("Surse"))detailPage(sourceId,"");
                });
            } catch(Exception e) {runOnUiThread(()->showError(e));}
        },"HistoryLab-OCR").start();
    }
    private void annotationDialog(long sourceId) {
        LinearLayout form=col();
        EditText quote=field(form,"Citat exact / pasaj (opțional)","",true);
        EditText note=field(form,"Întrebarea sau observația ta *","",true);
        EditText status=field(form,"Stare (de verificat, întrebare, comentariu)","De verificat",false);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Marginalie a istoricului")
            .setView(dialogScroll(form)).setNegativeButton("Anulează",null).setPositiveButton("Salvează",null).create();
        dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            if(value(note).isEmpty()){note.setError("Obligatoriu");return;}
            db.addAnnotation(sourceId,quote.getText().toString(),note.getText().toString(),value(status));
            dialog.dismiss();detailPage(sourceId,"");
        }));dialog.show();
    }

    private void highlightDialog(long sourceId) {
        EditText term=new EditText(this);term.setSingleLine(true);term.setHint("de ex. Bacău");
        new AlertDialog.Builder(this).setTitle("Localizează în original")
            .setMessage("Marcajele provin din coordonatele OCR. Verifică vizual imaginea; nu sunt interpretări.")
            .setView(term).setNegativeButton("Anulează",null)
            .setPositiveButton("Marchează",(d,w)->detailPage(sourceId,value(term))).show();
    }
    private void auditDialog(String entity,long id) {
        List<HistoryDb.Audit> history=db.audits(entity,id);
        LinearLayout form=col();
        if(history.isEmpty())form.addView(txt("Nu există revizuiri înregistrate.",14,MUTED,false));
        for(HistoryDb.Audit log:history) {
            LinearLayout item=panel(form);
            String date=new java.text.SimpleDateFormat("dd.MM.yyyy HH:mm",Locale.ROOT).format(new java.util.Date(log.when));
            item.addView(txt(date+" • "+log.action,14,INK,true));
            item.addView(spacer(5));
            if(!log.before.isEmpty()) {
                item.addView(txt("ÎNAINTE",11,MUTED,true));
                TextView before=txt(log.before,12,MUTED,false);before.setTextIsSelectable(true);item.addView(before);
                item.addView(spacer(7));
            }
            item.addView(txt("DUPĂ",11,ACCENT,true));
            TextView after=txt(log.after,12,INK,false);after.setTextIsSelectable(true);item.addView(after);
        }
        new AlertDialog.Builder(this).setTitle("Jurnalul istoricului")
            .setView(dialogScroll(form)).setPositiveButton("Închide",null).show();
    }

    // === INDEXARE DETERMINISTĂ ===
    private boolean matches(HistoryDb.Source source,HistoryDb.Rule rule) {
        return IndexMatcher.containsTerm(source.searchable(),rule.term);
    }
    private void indexPage() {
        heading(content,"Index controlat","Tu definești axele, etichetele și expresiile literale de căutat.");
        buttonFull(content,"+ Regulă nouă",this::addRuleDialog,true);
        LinearLayout expl=panel(content);
        expl.addView(txt("Exemplu",14,INK,true));
        expl.addView(txt("Axă: Localitate  •  Etichetă: Bacău  •  Expresie: Bacău\nPotrivirea este literală, fără deducerea contextului sau sensului.",13,MUTED,false));
        List<HistoryDb.Rule> rules=db.rules();
        List<HistoryDb.Source> sources=db.sources();
        content.addView(txt("REGULI DEFINITE ("+rules.size()+")",11,ACCENT,true));content.addView(spacer(8));
        if(rules.isEmpty())content.addView(txt("Adaugă reguli ca să începi sortarea automată.",13,MUTED,false));
        for(HistoryDb.Rule rule:rules) {
            List<HistoryDb.Source> hits=new ArrayList<>();
            for(HistoryDb.Source s:sources)if(matches(s,rule))hits.add(s);
            LinearLayout c=panel(content);
            c.addView(txt(rule.axis+"  /  "+rule.label,16,INK,true));c.addView(spacer(4));
            c.addView(txt("Expresie exactă: „"+rule.term+"”   •   "+hits.size()+" surse",12,MUTED,false));
            c.addView(spacer(9));
            buttonFull(c,"Vezi sursele marcate",()->filteredPage(rule.label,hits,rule.term),false);
            TextView remove=txt("Elimină regula",12,0xFF985E4C,false);pad(remove,4,7,4,7);c.addView(remove);
            remove.setOnClickListener(v->new AlertDialog.Builder(this)
                .setTitle("Elimini această regulă?").setMessage("Sursele originale nu se șterg.")
                .setNegativeButton("Anulează",null)
                .setPositiveButton("Elimină",(d,w)->{db.deleteRule(rule.id);indexPageRefresh();}).show());
        }
        if(rules.size()>=2) {
            content.addView(spacer(8));content.addView(txt("INTERSECȚII ÎNTRE AXE",11,ACCENT,true));
            content.addView(spacer(8));
            Map<String,List<HistoryDb.Source>> intersections=new LinkedHashMap<>();
            Map<String,String> markers=new HashMap<>();
            for(HistoryDb.Source source:sources) {
                for(int i=0;i<rules.size();i++)for(int j=i+1;j<rules.size();j++) {
                    HistoryDb.Rule a=rules.get(i),b=rules.get(j);
                    if(a.axis.equalsIgnoreCase(b.axis))continue;
                    if(!matches(source,a)||!matches(source,b))continue;
                    String key=a.axis+": "+a.label+" × "+b.axis+": "+b.label;
                    intersections.computeIfAbsent(key,k->new ArrayList<>()).add(source);
                    markers.put(key,a.term);
                }
            }
            if(intersections.isEmpty())content.addView(txt("Nu există încă suprapuneri literale între axe.",13,MUTED,false));
            int shown=0;
            for(Map.Entry<String,List<HistoryDb.Source>> entry:intersections.entrySet()) {
                if(shown++>=30)break;
                LinearLayout card=panel(content);
                card.addView(txt(entry.getKey(),14,INK,true));
                card.addView(txt(entry.getValue().size()+" sursă/surse",12,MUTED,false));
                card.setOnClickListener(v->filteredPage(entry.getKey(),entry.getValue(),markers.get(entry.getKey())));
            }
        }
    }
    private void indexPageRefresh(){renderTab("Index");}
    private void addRuleDialog() {
        LinearLayout form=col();
        EditText axis=field(form,"Numele axei (de ex. Localitate)","",false);
        EditText label=field(form,"Eticheta afișată (de ex. Bacău)","",false);
        EditText term=field(form,"Expresia EXACTĂ căutată în surse","",false);
        AlertDialog d=new AlertDialog.Builder(this).setTitle("Regulă deterministă")
            .setView(dialogScroll(form)).setNegativeButton("Anulează",null).setPositiveButton("Adaugă",null).create();
        d.setOnShowListener(a->d.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            if(value(axis).isEmpty()){axis.setError("Obligatoriu");return;}
            if(value(label).isEmpty()){label.setError("Obligatoriu");return;}
            if(value(term).isEmpty()){term.setError("Obligatoriu");return;}
            db.addRule(value(axis),value(label),value(term));d.dismiss();renderTab("Index");
        }));d.show();
    }
    private void filteredPage(String title,List<HistoryDb.Source> sources,String marker) {
        chrome("Index");buttonFull(content,"← Înapoi la index",()->renderTab("Index"),false);
        heading(content,title,sources.size()+" surse cu potriviri literale; semnificația rămâne de verificat.");
        for(HistoryDb.Source s:sources)sourceCard(content,s,marker);
    }

    // === CĂUTARE CU TRIMITERE LA SURSA ORIGINALĂ ===
    private void searchPage() {
        heading(content,"Căutare în atelier","Caută expresii exacte în metadate și transcrieri, fără completare automată.");
        LinearLayout c=panel(content);
        EditText query=field(c,"Cuvânt / expresie",lastSearch,false);
        buttonFull(c,"Caută și localizează",()->{
            lastSearch=value(query);renderTab("Căutare");
        },true);
        if(lastSearch.isEmpty()) {
            content.addView(txt("Exemplu: Bacău. Poți atinge un rezultat pentru a deschide originalul; cuvintele detectate de OCR pot fi evidențiate pe fotografie.",13,MUTED,false));
            return;
        }
        List<HistoryDb.Source> hits=new ArrayList<>();
        for(HistoryDb.Source s:db.sources())if(IndexMatcher.containsTerm(s.searchable(),lastSearch))hits.add(s);
        content.addView(txt(hits.size()+" surse potrivite pentru „"+lastSearch+"”",13,MUTED,false));
        content.addView(spacer(9));
        for(HistoryDb.Source s:hits) {
            sourceCard(content,s,lastSearch);
            String ocr=s.verified==1?s.corrected:s.raw;
            String snippet=snippet(ocr,lastSearch);
            if(!snippet.isEmpty()) {
                TextView context=txt("Pasaj OCR (verifică imaginea): …"+snippet+"…",12,MUTED,false);
                LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2);p.bottomMargin=dp(11);content.addView(context,p);
            }
        }
        if(hits.isEmpty())content.addView(txt("Nu există potriviri literale în datele locale.",14,MUTED,false));
    }
    private String snippet(String text,String needle) {
        int pos=IndexMatcher.normalize(text).indexOf(IndexMatcher.normalize(needle));
        if(pos<0)return "";
        int start=Math.max(0,pos-55),end=Math.min(text.length(),pos+needle.length()+90);
        return text.substring(Math.min(start,text.length()),end).replace('\n',' ');
    }

    // === FIȘE DE SINTEZĂ REDACTATE DE ISTORIC ===
    private void sheetsPage() {
        heading(content,"Fișe de sinteză","Doar istoricul scrie, combină, verifică și argumentează.");
        buttonFull(content,"+ Fișă / capitol nou",()->editSheetDialog(null),true);
        List<HistoryDb.Sheet> sheets=db.sheets();
        if(sheets.isEmpty()) {
            LinearLayout c=panel(content);c.addView(txt("Încă nu ai fișe",16,INK,true));
            c.addView(txt("Poți începe cu o problemă de cercetare, apoi atașa sursele folosite.",13,MUTED,false));
        }
        for(HistoryDb.Sheet s:sheets) {
            LinearLayout c=panel(content);
            c.addView(txt(s.title,17,INK,true));c.addView(spacer(5));
            c.addView(txt(s.content.length()>145?s.content.substring(0,145)+"…":s.content,13,MUTED,false));
            c.addView(spacer(6));c.addView(txt(db.sheetSources(s.id).size()+" surse asociate",12,ACCENT,true));
            c.setOnClickListener(v->sheetPage(s.id));
        }
    }
    private void editSheetDialog(HistoryDb.Sheet s) {
        LinearLayout form=col();
        form.addView(txt("Conținut redactat exclusiv de utilizator. HistoryLab nu produce sinteze.",13,MUTED,false));
        EditText title=field(form,"Titlu *",s==null?"":s.title,false);
        EditText text=field(form,"Sinteză / comentariu / capitol",s==null?"":s.content,true);
        text.setMinLines(12);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle(s==null?"Fișă nouă":"Editează fișa")
            .setView(dialogScroll(form)).setNegativeButton("Anulează",null)
            .setPositiveButton("Salvează",null).create();
        dialog.setOnShowListener(d->dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{
            if(value(title).isEmpty()){title.setError("Obligatoriu");return;}
            long id=db.saveSheet(s==null?0:s.id,value(title),text.getText().toString());
            dialog.dismiss();sheetPage(id);
        }));dialog.show();
    }
    private void sheetPage(long id) {
        HistoryDb.Sheet s=db.sheet(id);if(s==null){renderTab("Fișe");return;}
        chrome("Fișe");buttonFull(content,"← Înapoi la fișe",()->renderTab("Fișe"),false);
        heading(content,s.title,"Redactare personală, cu legături explicite spre surse.");
        LinearLayout c=panel(content);
        TextView document=txt(s.content.isEmpty()?"(fișă fără text)":s.content,15,INK,false);
        document.setTextIsSelectable(true);c.addView(document);
        c.addView(spacer(12));buttonFull(c,"Editează textul",()->editSheetDialog(s),true);
        buttonFull(c,"Exportă ca text (.txt)",()->exportSheet(s.id),false);
        buttonFull(c,"Copiază textul",()->copyText(s.content),false);
        buttonFull(c,"Jurnalul revizuirilor",()->auditDialog("sheet",s.id),false);
        LinearLayout links=panel(content);
        links.addView(txt("SURSE ASOCIATE DE TINE",12,ACCENT,true));links.addView(spacer(9));
        buttonFull(links,"Alege sursele acestei fișe",()->sheetLinksDialog(id),false);
        List<Long> linked=db.sheetSources(id);
        if(linked.isEmpty())links.addView(txt("Nu ai asociat încă surse.",13,MUTED,false));
        for(long sid:linked) {
            HistoryDb.Source source=db.source(sid);if(source==null)continue;
            TextView ref=txt("↗ "+source.title,14,INK,true);pad(ref,2,9,2,9);links.addView(ref);
            ref.setOnClickListener(v->detailPage(source.id,""));
        }
    }
    private void sheetLinksDialog(long sheetId) {
        List<HistoryDb.Source> available=db.sources();
        if(available.isEmpty()){toast("Adaugă întâi o sursă în arhivă.");return;}
        Set<Long> selected=new LinkedHashSet<>(db.sheetSources(sheetId));
        String[] titles=new String[available.size()];boolean[] checks=new boolean[available.size()];
        for(int i=0;i<available.size();i++) {
            titles[i]=available.get(i).title;checks[i]=selected.contains(available.get(i).id);
        }
        new AlertDialog.Builder(this).setTitle("Surse atașate fișei")
            .setMultiChoiceItems(titles,checks,(d,which,isChecked)->{
                long id=available.get(which).id;if(isChecked)selected.add(id);else selected.remove(id);
            })
            .setNegativeButton("Anulează",null)
            .setPositiveButton("Salvează legăturile",(d,w)->{
                db.replaceSheetLinks(sheetId,new ArrayList<>(selected));sheetPage(sheetId);
            }).show();
    }
    private void exportSheet(long id) {
        pendingSheetExport=id;
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);intent.setType("text/plain");
        intent.putExtra(Intent.EXTRA_TITLE,"HistoryLab-fisa-"+id+".txt");
        startActivityForResult(intent,EXPORT_SHEET);
    }
    private String sheetText(long sheetId) {
        HistoryDb.Sheet s=db.sheet(sheetId);if(s==null)return "";
        StringBuilder builder=new StringBuilder(s.title+"\n\n"+s.content+"\n\n---\nSURSE ASOCIATE (REFERINȚE ORIENTATIVE)\n");
        for(long id:db.sheetSources(sheetId)) {
            HistoryDb.Source source=db.source(id);
            if(source!=null)builder.append("- ").append(CitationFormatter.format(source.author,source.title,source.date,source.reference)).append('\n');
        }
        return builder.toString();
    }

    // === SETĂRI ȘI EXPORT ===
    private void settingsPage() {
        heading(content,"Atelierul tău","Datele rămân în spațiul privat al acestei aplicații.");
        LinearLayout a=panel(content);a.addView(txt("FUNCȚIONARE OFFLINE",12,ACCENT,true));a.addView(spacer(8));
        a.addView(txt("Aplicația nu solicită permisiunea INTERNET. Nu folosește AI generativ, analitice online sau sincronizare ascunsă. Camera poate fi deschisă prin aplicația instalată pe telefon.",14,INK,false));
        LinearLayout b=panel(content);b.addView(txt("LIMBI OCR INSTALATE",12,ACCENT,true));b.addView(spacer(8));
        b.addView(txt(OcrEngine.installedLanguages(this),14,INK,false));b.addView(spacer(8));
        b.addView(txt("Pachetul inițial: română și engleză. Pentru alte limbi, importă separat fișiere Tesseract .traineddata. Paleografia poate necesita modele specializate.",13,MUTED,false));
        buttonFull(b,"Importă model OCR (.traineddata)",this::pickModel,false);
        LinearLayout c=panel(content);c.addView(txt("COPIE DE SIGURANȚĂ",12,ACCENT,true));c.addView(spacer(8));
        c.addView(txt("Exportă sursele originale, metadatele, OCR-ul, regulile, notele și fișele într-un .zip. Păstrează fișierul în loc sigur.",13,MUTED,false));
        c.addView(spacer(10));buttonFull(c,"Exportă arhiva (.zip)",this::startBackup,true);
        c.addView(txt("Restaurarea din .zip nu este încă disponibilă în v0.1. Exportul nu este criptat.",12,0xFF955D45,false));
        LinearLayout d=panel(content);d.addView(txt("INTEGRITATE DOCUMENTARĂ",12,ACCENT,true));d.addView(spacer(7));
        d.addView(txt("Fiecare imagine originală este copiată octet cu octet în arhiva locală și identificată prin SHA-256. OCR-ul brut este separat de transcrierea corectată. Potrivirile din index nu reprezintă concluzii istorice.",13,INK,false));
        d.addView(spacer(7));d.addView(txt("HistoryLab 0.1 • prototip experimental; verifică orice transcriere și orice referință bibliografică.",12,MUTED,false));
    }
    private void pickModel() {
        Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("*/*");startActivityForResult(intent,PICK_MODEL);
    }
    private void startBackup() {
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("application/zip");intent.putExtra(Intent.EXTRA_TITLE,"HistoryLab-backup.zip");
        startActivityForResult(intent,EXPORT_BACKUP);
    }
    private String nameOf(Uri uri) {
        try(android.database.Cursor c=getContentResolver().query(uri,new String[]{android.provider.OpenableColumns.DISPLAY_NAME},null,null,null)) {
            if(c!=null&&c.moveToFirst())return c.getString(0);
        }catch(Exception ignored){}
        return uri.getLastPathSegment()==null?"":uri.getLastPathSegment();
    }
    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data) {
        super.onActivityResult(requestCode,resultCode,data);
        if(resultCode!=RESULT_OK)return;
        try {
            if(requestCode==TAKE_PHOTO) {
                if(pendingCamera==null||!pendingCamera.isFile())throw new Exception("Fotografia nu este disponibilă.");
                sourceMetadataDialog(Uri.fromFile(pendingCamera));
            } else if(requestCode==PICK_IMAGE) {
                if(data!=null&&data.getData()!=null)sourceMetadataDialog(data.getData());
            } else if(requestCode==PICK_MODEL) {
                if(data==null||data.getData()==null)return;
                Uri uri=data.getData();String name=nameOf(uri);
                try(InputStream in=getContentResolver().openInputStream(uri)) {
                    if(in==null)throw new Exception("Modelul nu se poate citi.");
                    OcrEngine.importModel(this,name,in);
                }
                toast("Model OCR importat: "+name);renderTab("Setări");
            } else if(requestCode==EXPORT_BACKUP) {
                if(data==null||data.getData()==null)return;
                Uri uri=data.getData();
                toast("Pregătesc arhiva locală...");
                new Thread(()->{
                    try{BackupExporter.export(getApplicationContext(),db,uri);
                        runOnUiThread(()->toast("Arhiva a fost exportată."));
                    }catch(Exception e){runOnUiThread(()->showError(e));}
                },"HistoryLab-Backup").start();
            } else if(requestCode==EXPORT_SHEET) {
                if(data==null||data.getData()==null)return;
                try(OutputStream out=getContentResolver().openOutputStream(data.getData())) {
                    if(out==null)throw new Exception("Nu s-a putut deschide destinația.");
                    out.write(sheetText(pendingSheetExport).getBytes(java.nio.charset.StandardCharsets.UTF_8));
                }
                toast("Fișa a fost exportată.");
            }
        } catch(Exception e) {showError(e);}
    }
}
