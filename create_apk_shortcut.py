import os
from pathlib import Path
import win32com.client

def create_apk_shortcut():
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop_dir = shell.SpecialFolders("Desktop")
        target_apk = os.path.join(desktop_dir, "JARVIS_Companion.apk")

        # Create shortcut on Desktop
        shortcut_path = os.path.join(desktop_dir, "JARVIS Companion (Updated APK).lnk")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = "explorer.exe"
        shortcut.Arguments = f'/select,"{target_apk}"'
        shortcut.WorkingDirectory = str(desktop_dir)
        shortcut.Description = "Open & Send JARVIS Companion APK for Android Phone"
        shortcut.IconLocation = r"C:\Windows\System32\shell32.dll,194"
        shortcut.Save()

        print(f"[SUCCESS] Desktop shortcut created at: {shortcut_path}")
        return True
    except Exception as e:
        print(f"[ERROR] Could not create shortcut: {e}")
        return False

if __name__ == "__main__":
    create_apk_shortcut()
