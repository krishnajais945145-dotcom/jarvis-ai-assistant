import os
import json
import time
import uuid
import threading
import datetime
from pathlib import Path

REMINDERS_FILE = Path.home() / ".jarvis_cache" / "reminders.json"
REMINDERS_FILE.parent.mkdir(parents=True, exist_ok=True)

class ReminderManager:
    def __init__(self, on_reminder_trigger=None):
        self.on_reminder_trigger = on_reminder_trigger
        self.reminders = self.load_reminders()
        self.is_running = True
        self._thread = threading.Thread(target=self._check_loop, daemon=True)
        self._thread.start()

    def load_reminders(self) -> list:
        if REMINDERS_FILE.exists():
            try:
                with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_reminders(self):
        try:
            with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.reminders, f, indent=4)
        except Exception as e:
            print(f"[Reminders] Failed to save: {e}")

    def add_reminder(self, message: str, trigger_datetime: datetime.datetime) -> tuple[bool, str]:
        rem_id = str(uuid.uuid4())[:8]
        entry = {
            "id": rem_id,
            "message": message,
            "time": trigger_datetime.isoformat(),
            "triggered": False
        }
        self.reminders.append(entry)
        self.save_reminders()
        readable_time = trigger_datetime.strftime("%I:%M %p on %d %b")
        return True, f"Reminder set for '{message}' at {readable_time}."

    def _check_loop(self):
        while self.is_running:
            now = datetime.datetime.now()
            modified = False
            for rem in self.reminders:
                if not rem.get("triggered", False):
                    rem_time = datetime.datetime.fromisoformat(rem["time"])
                    if now >= rem_time:
                        rem["triggered"] = True
                        modified = True
                        if self.on_reminder_trigger:
                            self.on_reminder_trigger(rem["message"])
            if modified:
                self.save_reminders()
            time.sleep(5)
