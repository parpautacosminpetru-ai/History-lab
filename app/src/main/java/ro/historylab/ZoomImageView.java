package ro.historylab;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.RectF;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;

import java.util.ArrayList;
import java.util.List;

/** Vizualizare a originalului, fără retușare. Pinch-to-zoom și marcaje OCR provizorii. */
public final class ZoomImageView extends View {
    private Bitmap image;
    private List<HistoryDb.OcrBox> boxes=new ArrayList<>();
    private String highlight="";
    private int ocrW=0,ocrH=0;
    private float zoom=1f,panX=0f,panY=0f,prevX,prevY;
    private final ScaleGestureDetector scaleDetector;
    private final Paint imagePaint=new Paint(Paint.FILTER_BITMAP_FLAG);
    private final Paint fillPaint=new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint edgePaint=new Paint(Paint.ANTI_ALIAS_FLAG);

    public ZoomImageView(Context context) {
        super(context);
        setLayerType(View.LAYER_TYPE_SOFTWARE,null);
        fillPaint.setColor(0x55E2AC4C);fillPaint.setStyle(Paint.Style.FILL);
        edgePaint.setColor(0xFFE09A21);edgePaint.setStrokeWidth(2f);edgePaint.setStyle(Paint.Style.STROKE);
        scaleDetector=new ScaleGestureDetector(context,new ScaleGestureDetector.SimpleOnScaleGestureListener() {
            @Override public boolean onScale(ScaleGestureDetector detector) {
                zoom=Math.max(1f,Math.min(8f,zoom*detector.getScaleFactor()));invalidate();return true;
            }
        });
    }
    public void setContent(Bitmap image,List<HistoryDb.OcrBox> boxes,int w,int h,String needle) {
        this.image=image;this.boxes=boxes==null?new ArrayList<>():boxes;
        ocrW=w;ocrH=h;highlight=needle==null?"":needle;zoom=1f;panX=panY=0;invalidate();
    }
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        canvas.drawColor(0xFFEFEDE7);
        if(image==null)return;
        float base=Math.min((float)getWidth()/image.getWidth(),(float)getHeight()/image.getHeight());
        float s=base*zoom;
        float x=(getWidth()-image.getWidth()*s)/2+panX;
        float y=(getHeight()-image.getHeight()*s)/2+panY;
        Matrix matrix=new Matrix();matrix.setScale(s,s);matrix.postTranslate(x,y);
        canvas.save();canvas.concat(matrix);
        canvas.drawBitmap(image,0,0,imagePaint);
        if(!highlight.isEmpty()&&ocrW>0&&ocrH>0) {
            float ratioX=(float)image.getWidth()/ocrW;
            float ratioY=(float)image.getHeight()/ocrH;
            for(HistoryDb.OcrBox b:boxes) {
                // Pentru expresii lungi se evidențiază doar cuvintele OCR corespunzătoare.
                if(!IndexMatcher.containsTerm(highlight,b.word)&&!IndexMatcher.containsTerm(b.word,highlight))continue;
                RectF rect=new RectF(b.left*ratioX,b.top*ratioY,b.right*ratioX,b.bottom*ratioY);
                canvas.drawRect(rect,fillPaint);canvas.drawRect(rect,edgePaint);
            }
        }
        canvas.restore();
    }
    @Override public boolean onTouchEvent(MotionEvent e) {
        scaleDetector.onTouchEvent(e);
        switch(e.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:prevX=e.getX();prevY=e.getY();return true;
            case MotionEvent.ACTION_MOVE:
                if(!scaleDetector.isInProgress()&&zoom>1f) {
                    panX+=e.getX()-prevX;panY+=e.getY()-prevY;invalidate();
                }
                prevX=e.getX();prevY=e.getY();return true;
            case MotionEvent.ACTION_UP:
                performClick();return true;
            default:return true;
        }
    }
    @Override public boolean performClick() {super.performClick();return true;}
}
