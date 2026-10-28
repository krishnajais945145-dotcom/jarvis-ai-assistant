import os
import shutil
import winreg
import psutil
import subprocess
from core.safety import ALLOWED_APPLICATIONS

def resolve_app_path(app_name: str) -> str:
    """Dynamically resolve absolute executable path for Windows applications."""
    clean_name = app_name.lower().strip()
    
    # Direct system commands
    if clean_name in ["calc", "calculator"]:
        return "calc.exe"
    if clean_name in ["notepad"]:
        return "notepad.exe"
    if clean_name in ["explorer", "file explorer"]:
        return "explorer.exe"
    if clean_name in ["paint", "mspaint"]:
        return "mspaint.exe"
    if clean_name in ["cmd"]:
        return "cmd.exe"
    if clean_name in ["taskmgr", "task manager"]:
        return "taskmgr.exe"
    if clean_name.startswith("ms-"):
        return clean_name

    if clean_name in ["chrome", "google chrome"]:
        chrome_candidates = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LocalAppData", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for c in chrome_candidates:
            if c and os.path.isfile(c):
                return c
        target_names = ["chrome", "GoogleChrome"]
    elif clean_name in ["edge", "microsoft edge"]:
        target_names = ["msedge"]
    elif clean_name in ["vs code", "vscode", "code"]:
        target_names = ["code"]
    else:
        target_names = [clean_name]

    for t in target_names:
        # Check PATH first
        p = shutil.which(t)
        if p:
            return p

        # Check Registry App Paths
        for root in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
            try:
                with winreg.OpenKey(root, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{t}.exe") as k:
                    val, _ = winreg.QueryValueEx(k, "")
                    if os.path.exists(val):
                        return val
            except Exception:
                pass

        # Check standard directory locations
        search_roots = [
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
            os.environ.get("LocalAppData", ""),
            os.environ.get("AppData", "")
        ]
        for base in search_roots:
            if not base or not os.path.exists(base):
                continue
            for r, d, files in os.walk(base):
                for f in files:
                    if f.lower() in [f"{t}.exe", f"{t}.cmd", f"{t}.bat"]:
                        return os.path.join(r, f)
                # Limit depth search for speed
                if r.count(os.sep) - base.count(os.sep) > 3:
                    break

    return clean_name

def launch_application(app_name: str) -> tuple[bool, str]:
    """Launch verified desktop application using resolved system path."""
    app_key = app_name.lower().strip()
    matched_app = None

    for k in ALLOWED_APPLICATIONS.keys():
        if k in app_key or app_key in k:
            matched_app = k
            break

    if not matched_app:
        matched_app = app_key

    resolved = resolve_app_path(matched_app)

    try:
        if resolved.startswith("ms-"):
            os.system(f"start {resolved}")
        elif os.path.exists(resolved):
            os.startfile(resolved)
        else:
            # Fallback to start command
            os.system(f'start "" "{resolved}"')
        return True, f"Opened {matched_app.capitalize()}."
    except Exception as e:
        return False, f"Failed to launch {app_name}: {str(e)}"

def close_application(app_name: str) -> tuple[bool, str]:
    """Safely terminate a running application process."""
    app_key = app_name.lower().strip()
    proc_map = {
        "chrome": ["chrome.exe"],
        "google chrome": ["chrome.exe"],
        "edge": ["msedge.exe"],
        "microsoft edge": ["msedge.exe"],
        "notepad": ["notepad.exe"],
        "calculator": ["calculatorapp.exe", "calc.exe", "calculator.exe"],
        "calc": ["calculatorapp.exe", "calc.exe", "calculator.exe"],
        "vs code": ["code.exe"],
        "vscode": ["code.exe"],
        "paint": ["mspaint.exe"]
    }

    target_exes = proc_map.get(app_key, [f"{app_key}.exe"])
    killed = False
    try:
        for proc in psutil.process_iter(['name']):
            p_name = proc.info.get('name')
            if p_name and any(p_name.lower() == target.lower() for target in target_exes):
                proc.terminate()
                killed = True
        if killed:
            return True, f"Closed {app_name.capitalize()}."
        else:
            return False, f"No running instance of {app_name.capitalize()} found."
    except Exception as e:
        return False, f"Error closing {app_name}: {str(e)}"
