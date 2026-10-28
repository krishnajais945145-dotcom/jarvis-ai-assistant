import os
import sys
from pathlib import Path

def create_desktop_shortcut():
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop_dir = shell.SpecialFolders("Desktop")
        
        project_dir = Path(__file__).resolve().parent
        vbs_path = project_dir / "launch_jarvis.vbs"
        icon_path = project_dir / "assets" / "jarvis.ico"

        shortcut_path = os.path.join(desktop_dir, "JARVIS AI Assistant.lnk")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = "wscript.exe"
        shortcut.Arguments = f'"{str(vbs_path)}"'
        shortcut.WorkingDirectory = str(project_dir)
        if icon_path.exists():
            shortcut.IconLocation = str(icon_path)
        shortcut.Description = "JARVIS Voice AI Assistant for Windows"
        shortcut.save()
        print(f"[SUCCESS] Desktop shortcut created at: {shortcut_path}")
        return True
    except Exception as e:
        print(f"[WARNING] Could not create Windows shortcut: {e}")
        return False

if __name__ == "__main__":
    create_desktop_shortcut()
