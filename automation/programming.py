import os
import subprocess
from pathlib import Path
from core.safety import SafetyManager

safety = SafetyManager()

def open_vscode_project(project_path: str = None) -> tuple[bool, str]:
    if not project_path:
        project_path = str(Path.home() / "Documents" / "JarvisProjects")

    target = Path(project_path).resolve()
    target.mkdir(parents=True, exist_ok=True)

    if not safety.is_path_safe(str(target)):
        return False, "Project path is outside approved directory."

    try:
        subprocess.Popen(f'code "{str(target)}"', shell=True)
        return True, f"Opened VS Code at {target.name}."
    except Exception as e:
        return False, f"Failed to open VS Code: {str(e)}"

def diagnose_code_issue(error_message: str) -> str:
    """Provide quick, beginner-friendly Hinglish diagnostics for common programming errors."""
    err_low = error_message.lower()
    if "syntaxerror" in err_low:
        return "Ye SyntaxError hai boss! Kahin colon ':', parenthesis '()', ya quotes band karna bhool gaye ho. Line number check karo."
    elif "indentationerror" in err_low:
        return "IndentationError hai! Python mein spaces aur tabs mix mat karo, har jagah 4 spaces use karo."
    elif "modulenotfounderror" in err_low or "no module named" in err_low:
        return "ModuleNotFound error! Library install nahi hai. Terminal mein 'pip install <library_name>' chala ke install kar lo."
    elif "typeerror" in err_low:
        return "TypeError hai! Lagta hai string aur integer ko direct add ya concatenate karne ki koshish kar rahe ho."
    elif "indexerror" in err_low:
        return "IndexError: list ki limit se bahar index access kar rahe ho. List ki length 'len()' se pehle verify karo."
    elif "keyerror" in err_low:
        return "KeyError! Dictionary mein ye key exist nahi karti. '.get()' method use karo safely access karne ke liye."
    else:
        return "Error message analyse kiya maine. Traceback ki aakhiri 2 lines check karo aur variables ki values print karke debug karo."
