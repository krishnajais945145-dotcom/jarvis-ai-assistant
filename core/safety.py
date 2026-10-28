import os
from pathlib import Path

# Safe Allowlist for Applications
ALLOWED_APPLICATIONS = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "file explorer": "explorer",
    "explorer": "explorer",
    "cmd": "cmd",
    "terminal": "wt",
    "task manager": "taskmgr",
    "paint": "mspaint",
    "settings": "ms-settings:"
}

# Operations requiring explicit confirmation
CRITICAL_OPERATIONS = [
    "shutdown",
    "restart",
    "delete_file",
    "delete_folder",
    "format_disk",
    "kill_critical_process"
]

class SafetyManager:
    def __init__(self, approved_roots=None):
        if approved_roots is None:
            self.approved_roots = [
                Path.home(),
                Path.home() / "Documents",
                Path.home() / "Desktop",
                Path.home() / "Downloads",
                Path.home() / "Pictures",
                Path.home() / "Videos",
                Path.home() / "Music"
            ]
        else:
            self.approved_roots = [Path(p) for p in approved_roots]

    def is_path_safe(self, target_path: str) -> bool:
        """Ensure file operations stay within safe user files and outside destructive system locations."""
        try:
            target = Path(target_path).resolve()
            # Prevent modifying critical Windows OS system root
            win_dir = Path(os.environ.get("SystemRoot", "C:\\Windows")).resolve()
            if win_dir in target.parents:
                return False
            for root in self.approved_roots:
                root_res = root.resolve()
                if root_res in target.parents or root_res == target:
                    return True
            # Allow existing user disk partitions if not in Windows directory
            return target.exists()
        except Exception:
            return False

    def is_app_allowed(self, app_name: str) -> bool:
        clean = app_name.lower().strip()
        return clean in ALLOWED_APPLICATIONS

    def requires_confirmation(self, action_name: str) -> bool:
        return action_name.lower().strip() in CRITICAL_OPERATIONS
