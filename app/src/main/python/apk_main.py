"""نقطة دخول بايثون داخل التطبيق: يشغّل لوحة البوت من المجلد القابل للكتابة (filesDir/botvi)."""
import os, sys, runpy

def run(home):
    os.environ["BOTVI_APK"] = "1"
    os.environ["BOTVI_HOME"] = home
    if home not in sys.path: sys.path.insert(0, home)
    os.chdir(home)
    runpy.run_path(os.path.join(home, "panel.py"), run_name="__main__")
