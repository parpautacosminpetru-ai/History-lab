package ro.historytool.mobile;

import android.graphics.Bitmap;
import android.graphics.pdf.PdfRenderer;
import android.os.ParcelFileDescriptor;
import android.util.Base64;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;

/** Render exactly the original PDF page. Text evidence is presented separately. */
public final class PdfRender {
    private PdfRender() {}
    public static String renderBase64(String path, int index, double zoom) throws IOException {
        File file = new File(path);
        try (ParcelFileDescriptor fd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY);
             PdfRenderer renderer = new PdfRenderer(fd)) {
            if (index < 0 || index >= renderer.getPageCount()) throw new IOException("Page index invalid");
            try (PdfRenderer.Page page = renderer.openPage(index)) {
                double scale = Math.min(2.0, Math.max(0.7, zoom));
                int w = (int)Math.max(1,Math.round(page.getWidth()*scale));
                int h = (int)Math.max(1,Math.round(page.getHeight()*scale));
                if ((long)w*h > 12_000_000) {
                    double k=Math.sqrt(12_000_000.0 / ((double)w*h));
                    w=Math.max(1,(int)(w*k));h=Math.max(1,(int)(h*k));
                }
                Bitmap image = Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
                image.eraseColor(0xFFFFFFFF);
                try {
                    page.render(image,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                    ByteArrayOutputStream stream = new ByteArrayOutputStream();
                    if (!image.compress(Bitmap.CompressFormat.PNG,100,stream)) throw new IOException("PNG encoding failed");
                    return Base64.encodeToString(stream.toByteArray(),Base64.NO_WRAP);
                } finally { image.recycle(); }
            }
        }
    }
}
