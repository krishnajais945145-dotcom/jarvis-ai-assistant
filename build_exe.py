import subprocess
import sys
import os

print("=" * 60)
print("Building Standalone Windows Application for JARVIS...")
print("=" * 60)

cmd = [
    sys.executable,
    "-m", "PyInstaller",
    "--noconfirm",
    "--onedir",
    "--windowed",
    "--name=JARVIS",
    "--icon=assets/jarvis.ico",
    "--collect-all=customtkinter",
    "--collect-all=pycaw",
    "--collect-all=screen_brightness_control",
    "app.py"
]

print("Executing command:", " ".join(cmd))
res = subprocess.run(cmd)
if res.returncode == 0:
    print("\n[SUCCESS] Build finished successfully! Output located at dist/JARVIS/JARVIS.exe")
else:
    print(f"\n[ERROR] Build exited with code {res.returncode}")
