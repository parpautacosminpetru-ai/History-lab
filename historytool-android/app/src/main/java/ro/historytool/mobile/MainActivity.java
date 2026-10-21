package ro.historytool.mobile;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.webkit.ConsoleMessage;
import android.webkit.WebResourceError;
import android.provider.OpenableColumns;
import android.graphics.Color;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import android.database.Cursor;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;

/**
 * historytool: Android frontend for the same *local* document and evidence API
 * as the desktop application. The server listens only on 127.0.0.1.
 */
public final class MainActivity extends Activity {
    private static final int SELECT_FILES = 7001, SAVE_FILE = 7002;
    private static final String LOCAL = "http://127.0.0.1:8765";
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService workers = Executors.newFixedThreadPool(2);
    private WebView web;
    private WebChromeClient.FileChooserParams fileChooser;
    private android.webkit.ValueCallback<Uri[]> fileCallback;
    private String downloadPath;
    private String startupError;
    private volatile boolean destroyed = false;
    private boolean ready = false;
    private long startupTime;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(0xFF172D46);
        showLoading("Pornire historytool…", "Pregătesc motorul local de cercetare.");
        startupTime = System.currentTimeMillis();
        workers.execute(() -> {
            try {
                prepareAssets();
                if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
                Thread server = new Thread(() -> {
                    try {
                        Python.getInstance().getModule("boot").callAttr("run_server", getFilesDir().getAbsolutePath());
                    } catch (Throwable e) { fail("Motorul local nu a pornit: " + e.getMessage()); }
                }, "historytool-python-server");
                server.setDaemon(true);
                server.start();
                pollServer();
            } catch (Throwable e) {fail("Eroare la inițializare: " + e.getMessage());}
        });
    }

    private void prepareAssets() throws IOException {
        int version;
        try { version = getPackageManager().getPackageInfo(getPackageName(), 0).versionCode; }
        catch (Exception e) { version = 10101; }
        int saved = getPreferences(MODE_PRIVATE).getInt("backend_version", 0);
        File backend = new File(getFilesDir(), "backend");
        if (saved != version || !new File(backend,"app.py").exists()) {
            copyAssetsRecursively("backend", backend);
            getPreferences(MODE_PRIVATE).edit().putInt("backend_version", version).apply();
        }
    }

    private void copyAssetsRecursively(String path, File dest) throws IOException {
        String[] children = getAssets().list(path);
        if (children != null && children.length > 0) {
            if (!dest.exists() && !dest.mkdirs()) throw new IOException("Nu se poate crea " + dest);
            for (String child : children) copyAssetsRecursively(path + "/" + child, new File(dest, child));
        } else {
            File parent = dest.getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) throw new IOException("Nu se poate crea folderul de lucru");
            try (InputStream in = getAssets().open(path); OutputStream out = new FileOutputStream(dest)) {
                byte[] buf = new byte[65536]; int len;
                while ((len = in.read(buf)) != -1) out.write(buf, 0, len);
            }
        }
    }

    private void pollServer() {
        if (destroyed || startupError != null || workers.isShutdown()) return;
        try {
            HttpURLConnection c = (HttpURLConnection)new URL(LOCAL + "/api/health").openConnection();
            c.setConnectTimeout(900); c.setReadTimeout(1100);
            if (c.getResponseCode() == 200) {
                c.disconnect(); ready = true;
                if (!destroyed) ui.post(this::showBrowser);
                return;
            }
            c.disconnect();
        } catch (Exception ignored) { }
        if (System.currentTimeMillis()-startupTime > 120000) {
            fail("Motorul local nu a răspuns în 120 secunde. Închide și repornește aplicația.");
        } else {
            ui.postDelayed(() -> {
                if (destroyed || workers.isShutdown()) return;
                try { workers.execute(this::pollServer); }
                catch (RejectedExecutionException e) {
                    Log.w("historytool", "Oprire normală: verificarea serverului a fost anulată");
                }
            }, 650);
        }
    }

    private void fail(String message) {
        if (destroyed) return;
        Log.e("historytool",message);
        startupError = message;
        ui.post(() -> { if (!destroyed) showLoading("historytool nu a putut porni", message); });
    }

    private void showLoading(String heading, String detail) {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(android.view.Gravity.CENTER);
        root.setPadding(28, 28, 28, 28);
        root.setBackgroundColor(0xFFF5F9FD);
        TextView title = new TextView(this);
        title.setText(heading);title.setTextSize(23);title.setTextColor(0xFF173E70);
        title.setGravity(android.view.Gravity.CENTER);
        root.addView(title);
        ProgressBar spinner = new ProgressBar(this);
        LinearLayout.LayoutParams spinnerParams = new LinearLayout.LayoutParams(64,64);
        spinnerParams.topMargin=22;spinnerParams.bottomMargin=18;
        if (startupError == null) root.addView(spinner, spinnerParams);
        TextView subtitle = new TextView(this);
        subtitle.setText(detail);subtitle.setTextSize(14);subtitle.setTextColor(0xFF486481);
        subtitle.setGravity(android.view.Gravity.CENTER);
        root.addView(subtitle);
        setContentView(root);
    }

    private void showBrowser() {
        if (destroyed || web != null || isFinishing() || isDestroyed()) return;
        web = new WebView(this);
        web.setBackgroundColor(Color.WHITE);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(true);
        settings.setDefaultTextEncodingName("UTF-8");
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        settings.setBuiltInZoomControls(false);
        settings.setTextZoom(100);
        web.addJavascriptInterface(new MobileInterface(), "HistorytoolMobile");
        web.setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                Log.i("historytool", "WebView finished: " + url);
                view.evaluateJavascript("(document.body ? document.body.innerText.slice(0,130) : 'no body')", output -> Log.i("historytool", "DOM preview: " + output));
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest req, WebResourceError error) {
                Log.e("historytool", "WebView error " + req.getUrl() + ": " + error);
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String target = request.getUrl().toString();
                if (target.startsWith(LOCAL + "/api/") && !target.contains("/api/passages/")) {
                    saveUrl(target.substring(LOCAL.length()));return true;
                }
                if (!target.startsWith(LOCAL + "/")) {
                    try {startActivity(new Intent(Intent.ACTION_VIEW, request.getUrl()));}
                    catch (Exception e) { notifyUser("Nu se poate deschide legătura externă"); }
                    return true;
                }
                return false;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onConsoleMessage(ConsoleMessage m) {
                Log.i("historytool-js", m.message() + " ("+m.sourceId()+":"+m.lineNumber()+")");
                return true;
            }
            @Override public boolean onShowFileChooser(WebView w, android.webkit.ValueCallback<Uri[]> callback, FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/pdf","application/vnd.openxmlformats-officedocument.wordprocessingml.document","text/plain","text/markdown","application/octet-stream","image/png","image/jpeg"});
                intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true);
                try { startActivityForResult(intent, SELECT_FILES);return true; }
                catch (ActivityNotFoundException e) {fileCallback=null;callback.onReceiveValue(null);notifyUser("Selectorul de fișiere nu este disponibil");return false;}
            }
        });
        setContentView(web);
        web.loadUrl(LOCAL + "/");
    }

    public final class MobileInterface {
        @JavascriptInterface public void saveFile(String url) {
            if (url==null || !url.startsWith("/api/")) return;
            ui.post(() -> saveUrl(url));
        }
    }

    private void saveUrl(String path) {
        if (path == null || !path.startsWith("/api/")) return;
        downloadPath = path;
        String name = path.contains("/backup") ? "historytool-backup.zip" :
                path.contains("/export") ? "historytool-sinteza.md" :
                path.contains("/original") ? "historytool-original.pdf" : "historytool-document.txt";
        String mime = name.endsWith(".zip") ? "application/zip" : name.endsWith(".pdf") ? "application/pdf" : "text/markdown";
        Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType(mime);
        intent.putExtra(Intent.EXTRA_TITLE,name);
        try { startActivityForResult(intent,SAVE_FILE); }
        catch (ActivityNotFoundException e) {notifyUser("Nu este disponibilă salvarea fișierului");}
    }

    private void notifyUser(String text) { Toast.makeText(this,text,Toast.LENGTH_LONG).show(); }

    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data) {
        super.onActivityResult(requestCode,resultCode,data);
        if (requestCode == SELECT_FILES) {
            if(fileCallback != null) {
                Uri[] uris = null;
                if (resultCode == RESULT_OK && data != null) {
                    if (data.getClipData() != null) {
                        int n = data.getClipData().getItemCount();
                        uris = new Uri[n];
                        for (int i=0;i<n;i++) uris[i]=data.getClipData().getItemAt(i).getUri();
                    } else if(data.getData()!=null) uris = new Uri[]{data.getData()};
                }
                fileCallback.onReceiveValue(uris);fileCallback=null;
            }
        } else if (requestCode == SAVE_FILE && resultCode == RESULT_OK && data != null && data.getData() != null) {
            Uri dest=data.getData();String path=downloadPath;
            workers.execute(() -> {
                try {
                    URL url = new URL(LOCAL + path.replace("#", "%23"));
                    HttpURLConnection con = (HttpURLConnection)url.openConnection();
                    con.setConnectTimeout(10000);con.setReadTimeout(60000);
                    int response=con.getResponseCode();
                    if(response!=200)throw new IOException("HTTP " + response);
                    try(InputStream in=con.getInputStream();OutputStream out=getContentResolver().openOutputStream(dest)) {
                        if(out==null)throw new IOException("Destinație indisponibilă");
                        byte[] buf=new byte[65536];int n;
                        while((n=in.read(buf))!=-1)out.write(buf,0,n);
                    } finally { con.disconnect(); }
                    ui.post(() -> notifyUser("Fișier salvat în telefon"));
                } catch(Exception e){ui.post(() -> notifyUser("Eroare la export: "+e.getMessage()));}
            });
        }
    }

    @Override public void onBackPressed() {
        if (web!=null && web.canGoBack()) web.goBack();else super.onBackPressed();
    }

    @Override public void onDestroy() {
        destroyed = true;
        ui.removeCallbacksAndMessages(null);
        if (web != null) {web.removeJavascriptInterface("HistorytoolMobile");web.destroy();web=null;}
        workers.shutdownNow();super.onDestroy();
    }
}
