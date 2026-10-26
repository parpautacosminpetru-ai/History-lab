"""Reproducible Flutter platform scaffolding; preserve the existing HistoryLab app."""
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]/'app'
default_test=root/'test/widget_test.dart'
had_default_test=default_test.exists()
subprocess.run(['flutter','create','--no-pub','--platforms=windows,android','--org','ro.hui',
                '--project-name','hui_reader',str(root)],check=True)
if not had_default_test and default_test.exists() and 'MyApp' in default_test.read_text():
    default_test.unlink()  # Generated counter test does not belong to this application.
android='{http://schemas.android.com/apk/res/android}'
ET.register_namespace('android','http://schemas.android.com/apk/res/android')
for file in (root/'android/app/src').rglob('AndroidManifest.xml'):
    tree=ET.parse(file)
    for permission in list(tree.getroot().findall('uses-permission')):
        if permission.get(android+'name') in ('android.permission.INTERNET','android.permission.ACCESS_NETWORK_STATE'):
            tree.getroot().remove(permission)
    application=tree.getroot().find('application')
    if application is not None:application.set(android+'label','HUI Reader')
    tree.write(file,encoding='utf-8',xml_declaration=True)
gradle=root/'android/app/build.gradle.kts'
if gradle.exists():
    text=gradle.read_text()
    text=re.sub(r'minSdk\s*=\s*flutter.minSdkVersion','minSdk = 26',text)
    gradle.write_text(text)
print('Platforms prepared. Run flutter pub get inside hui/app.')
