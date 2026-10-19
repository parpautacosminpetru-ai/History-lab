package ro.historylab;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.core.content.FileProvider;
import androidx.webkit.WebViewAssetLoader;

import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;

import org.json.JSONObject;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.UUID;

/**
 * HistoryLab · Atlasul Explicit.
 *
 * Fotografia sursă este copiată nemodificată în stocarea privată.
 * ML Kit Text Recognition latin (model inclus în APK) realizează doar OCR.
 * Niciuna dintre clasificările istorice nu este produsă de Android sau de OCR.
 * Aplicația nu declară permisiunea INTERNET.
 */
public final class MainActivity extends Activity {
    private static final int OPEN_JSON = 501;
    private static final int SAVE_JSON = 502;
    private static final int PICK_PAGE = 503;
    private static final int CAPTURE_PAGE = 504;
    private static final long MAX_PAGE_BYTES = 18L * 1024L * 1024L;
    private static final String ASSET_ROOT = "https://appassets.androidplatform.net/assets/";
    private static final String IMAGE_ROOT = "https://appassets.androidplatform.net/pages/";

    private WebView webView;
    private ValueCallback<Uri[]> pendingUpload;
    private String pendingExport;
    private File pendingCameraFile;
    private WebViewAssetLoader assetLoader;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        File pageDir = new File(getFilesDir(), "page-images");
        if (!pageDir.exists()) pageDir.mkdirs();
        assetLoader = new WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
            .addPathHandler("/pages/", new WebViewAssetLoader.InternalStoragePathHandler(this, pageDir))
            .build();

        getWindow().setStatusBarColor(0xff18262d);
        getWindow().setNavigationBarColor(0xff18262d);

        webView = new WebView(this);
        setContentView(webView);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setJavaScriptCanOpenWindowsAutomatically(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        webView.addJavascriptInterface(new LocalExportBridge(), "HistoryBridge");
        webView.addJavascriptInterface(new OcrBridge(), "HistoryOCRBridge");
        webView.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                return !uri.toString().startsWith(ASSET_ROOT);
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> callback,
                FileChooserParams params) {
                if (pendingUpload != null) pendingUpload.onReceiveValue(null);
                pendingUpload = callback;
                try {
                    startActivityForResult(params.createIntent(), OPEN_JSON);
                    return true;
                } catch (ActivityNotFoundException ex) {
                    pendingUpload = null;
                    Toast.makeText(MainActivity.this, "Nu există selector de fișiere.", Toast.LENGTH_LONG).show();
                    return false;
                }
            }
        });

        webView.loadUrl(ASSET_ROOT + "index.html");
    }

    public final class OcrBridge {
        @JavascriptInterface public void capturePhoto() {runOnUiThread(MainActivity.this::startPhotoCapture);}
        @JavascriptInterface public void chooseImage() {runOnUiThread(MainActivity.this::startPhotoPicker);}
    }

    private void startPhotoPicker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("image/*");
        intent.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"image/jpeg","image/png","image/webp"});
        try {
            startActivityForResult(intent,PICK_PAGE);
        } catch (ActivityNotFoundException e) {
            reportOcrError("Nu există o aplicație pentru deschiderea fotografiilor.");
        }
    }

    private void startPhotoCapture() {
        File dir = new File(getCacheDir(),"captures");
        if (!dir.exists() && !dir.mkdirs()) {reportOcrError("Nu pot crea directorul camerei.");return;}
        try {
            pendingCameraFile = File.createTempFile("historylab-photo-", ".jpg", dir);
            Uri output = FileProvider.getUriForFile(this,getPackageName()+".fileprovider",pendingCameraFile);
            Intent intent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            intent.putExtra(MediaStore.EXTRA_OUTPUT,output);
            intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivityForResult(intent,CAPTURE_PAGE);
        } catch (Exception e) {
            reportOcrError("Camera nu a putut fi deschisă: "+e.getMessage());
        }
    }

    private void handlePageUri(Uri uri, String mime) {
        String extension;
        if ("image/png".equals(mime)) extension=".png";
        else if ("image/webp".equals(mime)) extension=".webp";
        else extension=".jpg";
        File target = new File(new File(getFilesDir(),"page-images"),"page-"+UUID.randomUUID()+extension);
        try(InputStream input=getContentResolver().openInputStream(uri);
            OutputStream output=new FileOutputStream(target)){
            if(input==null)throw new IllegalStateException("Fotografia nu poate fi citită.");
            byte[] buffer=new byte[16384];
            long count=0;int length;
            while((length=input.read(buffer))>=0){
                count+=length;
                if(count>MAX_PAGE_BYTES)throw new IllegalStateException("Fotografia depășește 18 MB.");
                output.write(buffer,0,length);
            }
            output.flush();
        } catch (Exception e) {
            target.delete();
            reportOcrError("Citire fotografie: "+e.getMessage());return;
        }
        final File immutablePhoto=target;
        final String url=IMAGE_ROOT+target.getName();
        try {
            InputImage inputImage=InputImage.fromFilePath(this,Uri.fromFile(target));
            TextRecognizer recognizer=TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
            recognizer.process(inputImage)
                .addOnSuccessListener(result->sendPage(url,mime,result.getText()))
                .addOnFailureListener(error->{
                    // Păstrează imaginea chiar și dacă OCR-ul nu a identificat text.
                    sendPage(url,mime,"");
                    runOnUiThread(()->Toast.makeText(this,
                        "OCR fără rezultat: verifică fotografia și transcrie manual.",Toast.LENGTH_LONG).show());
                })
                .addOnCompleteListener(result->recognizer.close());
        } catch (Exception e) {
            // Fișierul original este păstrat; utilizatorul îl poate transcrie manual.
            sendPage(url,mime,"");
        }
    }

    private void sendPage(String url, String mime, String text) {
        try {
            JSONObject value=new JSONObject();
            value.put("imageUrl",url);
            value.put("mimeType",mime);
            value.put("text",text);
            value.put("engine","mlkit-latin-v2-bundled");
            String encoded=JSONObject.quote(value.toString());
            runOnUiThread(()->webView.evaluateJavascript(
                "window.HistoryOCR && window.HistoryOCR.onPageReady("+encoded+");",null));
        } catch(Exception e) {reportOcrError(e.getMessage());}
    }

    private void reportOcrError(String message) {
        String encoded=JSONObject.quote(message==null?"Eroare necunoscută":message);
        runOnUiThread(()->webView.evaluateJavascript(
            "window.HistoryOCR && window.HistoryOCR.onError("+encoded+");",null));
    }

    public final class LocalExportBridge {
        @JavascriptInterface public void saveJson(String json) {
            runOnUiThread(()->{
                if(pendingExport!=null){
                    Toast.makeText(MainActivity.this,"Finalizează mai întâi exportul curent.",Toast.LENGTH_SHORT).show();
                    return;
                }
                pendingExport=json;
                Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);
                intent.setType("application/json");
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                String stamp=new SimpleDateFormat("yyyy-MM-dd",Locale.ROOT).format(new Date());
                intent.putExtra(Intent.EXTRA_TITLE,"HistoryLab-"+stamp+".json");
                try {startActivityForResult(intent,SAVE_JSON);}
                catch(ActivityNotFoundException e){
                    pendingExport=null;
                    Toast.makeText(MainActivity.this,"Nu pot deschide salvarea fișierului.",Toast.LENGTH_LONG).show();
                }
            });
        }
    }

    @Override protected void onActivityResult(int requestCode,int resultCode,Intent result) {
        super.onActivityResult(requestCode,resultCode,result);
        if(requestCode==OPEN_JSON) {
            if(pendingUpload!=null){
                pendingUpload.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode,result));
                pendingUpload=null;
            }
        } else if(requestCode==SAVE_JSON) {
            String value=pendingExport;pendingExport=null;
            if(resultCode!=RESULT_OK||result==null||result.getData()==null||value==null)return;
            try(OutputStream out=getContentResolver().openOutputStream(result.getData())){
                if(out==null)throw new IllegalStateException("Fișierul nu poate fi scris.");
                out.write(value.getBytes(StandardCharsets.UTF_8));
                out.flush();
                Toast.makeText(this,"Arhiva HistoryLab a fost salvată.",Toast.LENGTH_LONG).show();
            }catch(Exception ex){
                Toast.makeText(this,"Export nereușit: "+ex.getMessage(),Toast.LENGTH_LONG).show();
            }
        } else if(requestCode==PICK_PAGE) {
            if(resultCode!=RESULT_OK||result==null||result.getData()==null){
                reportOcrError("Selectarea fotografiei a fost anulată.");return;
            }
            Uri uri=result.getData();
            String mime=getContentResolver().getType(uri);
            if(!"image/jpeg".equals(mime)&&!"image/png".equals(mime)&&!"image/webp".equals(mime)){
                reportOcrError("Selectează o fotografie JPEG, PNG sau WebP.");return;
            }
            handlePageUri(uri,mime);
        } else if(requestCode==CAPTURE_PAGE) {
            File photo=pendingCameraFile;pendingCameraFile=null;
            if(resultCode!=RESULT_OK||photo==null||!photo.isFile()||photo.length()==0) {
                if(photo!=null)photo.delete();
                reportOcrError("Fotografierea a fost anulată.");return;
            }
            handlePageUri(Uri.fromFile(photo),"image/jpeg");
            photo.delete();
        }
    }

    @Override protected void onDestroy(){
        if(pendingUpload!=null){pendingUpload.onReceiveValue(null);pendingUpload=null;}
        if(webView!=null){
            webView.removeJavascriptInterface("HistoryBridge");
            webView.removeJavascriptInterface("HistoryOCRBridge");
            webView.destroy();
        }
        super.onDestroy();
    }
}
