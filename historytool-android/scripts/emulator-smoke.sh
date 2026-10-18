#!/usr/bin/env bash
set -euo pipefail

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
adb shell screencap -p /sdcard/historytool-proof.png
adb pull /sdcard/historytool-proof.png historytool-emulator.png

echo 'historytool ANDROID END-TO-END SMOKE PASS'