from pathlib import Path
import os
import subprocess
import sys

sdk=Path(os.environ.get('ANDROID_HOME') or os.environ['ANDROID_SDK_ROOT'])
aapt=sorted((sdk/'build-tools').glob('*/aapt*'))
aapt=[path for path in aapt if path.name in ('aapt','aapt.exe')][-1]
result=subprocess.run([str(aapt),'dump','permissions',sys.argv[1]],check=True,capture_output=True,text=True)
print(result.stdout)
for forbidden in ('android.permission.INTERNET','android.permission.ACCESS_NETWORK_STATE'):
    if forbidden in result.stdout:raise SystemExit('Forbidden Reader network permission: '+forbidden)
