package ro.historytool.mobile;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.pdf.PdfRenderer;
import android.os.ParcelFileDescriptor;
import com.google.android.gms.tasks.Tasks;
import com.google.mlkit.vision.common.InputImage;
import com.google.mlkit.vision.text.Text;
import com.google.mlkit.vision.text.TextRecognition;
import com.google.mlkit.vision.text.TextRecognizer;
import com.google.mlkit.vision.text.latin.TextRecognizerOptions;
import java.io.File;
import java.io.IOException;
import java.util.concurrent.TimeUnit;

/** On-device OCR. Its result must be verified against the original. */
public final class OfflineOcr {
    private OfflineOcr() {}
    private static String recognizeBitmap(Bitmap bitmap) throws Exception {
        TextRecognizer recognizer=TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS);
        try {
            Text text=Tasks.await(recognizer.process(InputImage.fromBitmap(bitmap,0)),90,TimeUnit.SECONDS);
            return text.getText();
        } finally { recognizer.close(); }
    }
    public static String recognizePdfPage(String filename,int pageIndex) throws Exception {
        try(ParcelFileDescriptor fd=ParcelFileDescriptor.open(new File(filename),ParcelFileDescriptor.MODE_READ_ONLY);
            PdfRenderer pdf=new PdfRenderer(fd)) {
            if(pageIndex<0||pageIndex>=pdf.getPageCount())throw new IOException("Pagină PDF inexistentă");
            try(PdfRenderer.Page page=pdf.openPage(pageIndex)) {
                double scale=Math.min(2.5,Math.max(1.5,2200.0/Math.max(page.getWidth(),page.getHeight())));
                int w=(int)Math.round(page.getWidth()*scale),h=(int)Math.round(page.getHeight()*scale);
                if((long)w*h>8000000L){double k=Math.sqrt(8000000.0/((double)w*h));w=(int)(w*k);h=(int)(h*k);}
                Bitmap bitmap=Bitmap.createBitmap(Math.max(1,w),Math.max(1,h),Bitmap.Config.ARGB_8888);
                try{
                    bitmap.eraseColor(0xFFFFFFFF);
                    page.render(bitmap,null,null,PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY);
                    return recognizeBitmap(bitmap);
                }finally{bitmap.recycle();}
            }
        }
    }
    public static String recognizeImage(String filename) throws Exception {
        BitmapFactory.Options probe=new BitmapFactory.Options();probe.inJustDecodeBounds=true;
        BitmapFactory.decodeFile(filename,probe);
        if(probe.outWidth<=0||probe.outHeight<=0)throw new IOException("Imagine nerecunoscută");
        BitmapFactory.Options o=new BitmapFactory.Options();o.inSampleSize=1;
        while((long)(probe.outWidth/o.inSampleSize)*(probe.outHeight/o.inSampleSize)>8000000L)o.inSampleSize*=2;
        Bitmap bitmap=BitmapFactory.decodeFile(filename,o);
        if(bitmap==null)throw new IOException("Imaginea nu a putut fi deschisă");
        try{return recognizeBitmap(bitmap);}finally{bitmap.recycle();}
    }
}
