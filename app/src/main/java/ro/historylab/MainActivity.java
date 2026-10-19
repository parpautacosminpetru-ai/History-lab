package ro.historylab;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import androidx.webkit.WebViewAssetLoader;

import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * Înveliș Android complet offline. Logica de indexare este în assets (JavaScript);
 * păstrarea locală se face prin IndexedDB, fără server și fără permisiunea INTERNET.
 * Transferul de fișiere se face numai la comanda utilizatorului, prin SAF Android.
 */
public final class MainActivity extends Activity {
    private static final int OPEN_JSON = 501;
    private static final int SAVE_JSON = 502;
    private static final String ASSET_ROOT = "https://appassets.androidplatform.net/assets/";

    private WebView webView;
    private ValueCallback<Uri[]> pendingUpload;
    private String pendingExport;
    private WebViewAssetLoader assetLoader;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        assetLoader = new WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
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
        webView.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(
                WebView view, WebResourceRequest request) {
                return assetLoader.shouldInterceptRequest(request.getUrl());
            }

            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                return !uri.toString().startsWith(ASSET_ROOT);
            }
        });
        webView.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView webView,
                ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
                if (pendingUpload != null) pendingUpload.onReceiveValue(null);
                pendingUpload = filePathCallback;
                try {
                    Intent intent = fileChooserParams.createIntent();
                    startActivityForResult(intent, OPEN_JSON);
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

    public final class LocalExportBridge {
        @JavascriptInterface public void saveJson(String json) {
            runOnUiThread(() -> {
                if (pendingExport != null) {
                    Toast.makeText(MainActivity.this, "Finalizează mai întâi exportul curent.", Toast.LENGTH_SHORT).show();
                    return;
                }
                pendingExport = json;
                Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                intent.setType("application/json");
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                String stamp = new SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(new Date());
                intent.putExtra(Intent.EXTRA_TITLE, "HistoryLab-" + stamp + ".json");
                try {
                    startActivityForResult(intent, SAVE_JSON);
                } catch (ActivityNotFoundException ex) {
                    pendingExport = null;
                    Toast.makeText(MainActivity.this, "Nu există aplicație pentru salvarea fișierului.", Toast.LENGTH_LONG).show();
                }
            });
        }
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent result) {
        super.onActivityResult(requestCode, resultCode, result);
        if (requestCode == OPEN_JSON) {
            if (pendingUpload != null) {
                pendingUpload.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, result));
                pendingUpload = null;
            }
        } else if (requestCode == SAVE_JSON) {
            String value = pendingExport;
            pendingExport = null;
            if (resultCode != RESULT_OK || result == null || result.getData() == null || value == null) return;
            try (OutputStream out = getContentResolver().openOutputStream(result.getData())) {
                if (out == null) throw new IllegalStateException("Fișierul nu poate fi scris.");
                byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
                out.write(bytes);
                out.flush();
                Toast.makeText(this, "Arhiva HistoryLab a fost salvată.", Toast.LENGTH_LONG).show();
            } catch (Exception ex) {
                Toast.makeText(this, "Export nereușit: " + ex.getMessage(), Toast.LENGTH_LONG).show();
            }
        }
    }

    @Override protected void onDestroy() {
        if (pendingUpload != null) {
            pendingUpload.onReceiveValue(null);
            pendingUpload = null;
        }
        if (webView != null) {
            webView.removeJavascriptInterface("HistoryBridge");
            webView.destroy();
        }
        super.onDestroy();
    }
}
