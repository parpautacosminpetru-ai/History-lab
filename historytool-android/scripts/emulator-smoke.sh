#!/usr/bin/env bash
set -euo pipefail

capture_diagnostics() {
  adb logcat -d -v time -s AndroidRuntime:E historytool:V historytool-js:V chromium:W > historytool-emulator-log.txt || true
  adb shell uiautomator dump /sdcard/historytool-tree.xml || true
  adb pull /sdcard/historytool-tree.xml historytool-emulator-tree.xml || true
  adb shell screencap -p /sdcard/historytool-proof.png || true
  adb pull /sdcard/historytool-proof.png historytool-emulator.png || true
}
trap capture_diagnostics EXIT

adb install -r android-test-apk/app-debug.apk
adb shell am start -W -n ro.historytool.mobile/.MainActivity
adb forward tcp:8765 tcp:8765

ready=0
for i in $(seq 1 90); do
  if curl -fsS --max-time 3 http://127.0.0.1:8765/api/health -o /tmp/historytool-health.json; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" != 1 ]; then
  adb logcat -d -s AndroidRuntime:E python.stderr:E | tail -n 200 || true
  exit 1
fi
cat /tmp/historytool-health.json
python -c "import json; assert json.load(open('/tmp/historytool-health.json'))['status']=='ok'"
printf 'In anul 1475 Moldova a fost mentionata intr-un document de proba.\n' >/tmp/historytool-smoke.txt
curl -fSs -F 'files=@/tmp/historytool-smoke.txt;type=text/plain' http://127.0.0.1:8765/api/sources/upload -o /tmp/historytool-upload.json
cat /tmp/historytool-upload.json
curl -fSs -X POST http://127.0.0.1:8765/api/index/start >/tmp/historytool-index.json
for i in $(seq 1 50); do
  curl -fsS http://127.0.0.1:8765/api/index/progress -o /tmp/historytool-progress.json
  if python -c "import json,sys;sys.exit(json.load(open('/tmp/historytool-progress.json'))['job']['status']=='running')"; then break; fi
  sleep 1
done
python -c "import json; d=json.load(open('/tmp/historytool-progress.json')); print(d); assert d['job']['status']=='done'"
curl -fSsG --data-urlencode 'q=Moldova' http://127.0.0.1:8765/api/query -o /tmp/historytool-query.json
python -c "import json; d=json.load(open('/tmp/historytool-query.json')); print(d.get('total'), 'hits'); assert d.get('total',0)>0"
sleep 12
adb shell uiautomator dump /sdcard/historytool-tree.xml >/dev/null
adb pull /sdcard/historytool-tree.xml historytool-emulator-tree.xml >/dev/null
if ! grep -Eiq 'index universal|historytool|bibliotec' historytool-emulator-tree.xml; then
  echo 'ANDROID UI TEST FAILED: the interface is not visible in accessibility tree'
  exit 1
fi

echo 'historytool ANDROID END-TO-END SMOKE PASS'
# Add a genuine scanned-PDF test. The PDF contains only an embedded raster image.
python -m pip install --quiet Pillow reportlab
python - <<'PY'
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
im=Image.new('RGB',(1500,2100),'white');draw=ImageDraw.Draw(im)
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',100)
for y,t in [(250,'ARHIVA MOLDOVA'),(480,'DOCUMENT 1475'),(720,'CERCETARE ISTORICA')]:
    draw.text((90,y),t,font=font,fill='black')
pdf=canvas.Canvas('/tmp/historytool-scan.pdf',pagesize=(600,840))
pdf.drawImage(ImageReader(im),0,0,width=600,height=840)
pdf.save()
PY
curl -fsS -F 'files=@/tmp/historytool-scan.pdf;type=application/pdf' http://127.0.0.1:8765/api/sources/upload >/tmp/historytool-ocr-upload.json
curl -fsS -X POST 'http://127.0.0.1:8765/api/index/start?ocr=true' >/dev/null
for i in $(seq 1 100); do
  curl -fsS http://127.0.0.1:8765/api/index/progress -o /tmp/historytool-ocr-progress.json
  if python -c "import json,sys;sys.exit(json.load(open('/tmp/historytool-ocr-progress.json'))['job']['status']=='running')"; then break; fi
  sleep 2
done
python - <<'PY'
import json
d=json.load(open('/tmp/historytool-ocr-progress.json'))
print('Scanned OCR result',d['job'])
assert d['job']['status']=='done'
assert any(x.get('passages',0)>0 for x in d['job']['result']['results']), 'Scanned PDF OCR returned zero passages'
PY
curl -fsSG --data-urlencode 'q=ARHIVA' http://127.0.0.1:8765/api/query > /tmp/historytool-ocr-query.json
python - <<'PY'
import json
j=json.load(open('/tmp/historytool-ocr-query.json'))
print('OCR search result count:',j['total'])
assert j['total']>0
PY
OCR_PID=$(python -c "import json; print(json.load(open('/tmp/historytool-ocr-query.json'))['hits'][0]['id'])")
curl -fsS "http://127.0.0.1:8765/api/passages/$OCR_PID/image" > /tmp/historytool-ocr-original.png
python -c "assert open('/tmp/historytool-ocr-original.png','rb').read(8)==bytes.fromhex('89504e470d0a1a0a')"
echo 'OCR PDF / passage / image tests passed'

curl -fsS -H 'Content-Type: application/json' -d '{"title":"Test de sinteza","body":"Notite salvate local"}' http://127.0.0.1:8765/api/notes >/tmp/historytool-note.json
NOTE_ID=$(python -c "import json;print(json.load(open('/tmp/historytool-note.json'))['id'])")
curl -fsS -H 'Content-Type: application/json' -d "{\"passage_id\":$OCR_PID}" "http://127.0.0.1:8765/api/notes/$NOTE_ID/evidence" >/dev/null
curl -fsS 'http://127.0.0.1:8765/api/backup' > /tmp/historytool-backup.zip
python -c "import zipfile;z=zipfile.ZipFile('/tmp/historytool-backup.zip');assert z.testzip() is None"
adb shell am force-stop ro.historytool.mobile
adb shell am start -W -n ro.historytool.mobile/.MainActivity
RESTART_OK=0
for i in $(seq 1 90); do
  if curl -fsS --max-time 3 http://127.0.0.1:8765/api/health -o /tmp/historytool-restart.json; then RESTART_OK=1; break; fi
  sleep 2
done
[ "$RESTART_OK" = 1 ] || { echo "App failed to restart"; exit 1; }
python - <<'PY'
import json
j=json.load(open('/tmp/historytool-restart.json'))
assert j['sources']>=2 and j['indexed']>=2,j
PY
curl -fsS http://127.0.0.1:8765/api/notes >/tmp/historytool-notes-after.json
python - <<'PY'
import json
d=json.load(open('/tmp/historytool-notes-after.json'))
assert any(n['title']=='Test de sinteza' and n['evidence'] for n in d['notes']),d
PY
echo 'Data, citations and notes persist after Android restart'
sleep 4
adb shell uiautomator dump /sdcard/historytool-tree.xml >/dev/null
adb pull /sdcard/historytool-tree.xml historytool-emulator-tree.xml >/dev/null
grep -Eiq 'index universal|historytool|bibliotec' historytool-emulator-tree.xml
echo 'historytool 1.0.2 ANDROID OCR + PERSISTENCE + UI PASS'
