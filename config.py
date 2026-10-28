import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

CONFIG_FILE = BASE_DIR / "user_settings.json"

LOCAL_APPDATA = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
MEMORY_DIR = Path(LOCAL_APPDATA) / "JarvisAssistant" / "memory"
MEMORY_DB_PATH = MEMORY_DIR / "jarvis_memory.db"

DEFAULT_CONFIG = {
    "wake_word": "hey jarvis",
    "wake_word_sensitivity": 0.5,
    "wake_word_engine": "keyword",  # 'keyword' or 'vosk'
    "voice_engine": "edge-tts",      # 'edge-tts' (high quality) or 'pyttsx3' (offline)
    "voice_female_en": "en-IN-NeerjaNeural",
    "voice_female_hi": "hi-IN-SwaraNeural",
    "voice_rate": "+0%",
    "voice_volume": "+0%",
    "language_mode": "auto",         # 'auto', 'hinglish', 'hindi', 'english'
    "preferred_llm": "gemini",       # 'gemini', 'openai', or 'offline'
    "personality_tone": "witty_sarcastic",
    "approved_workspace": str(Path.home() / "Documents" / "JarvisProjects"),
    "notes_dir": str(Path.home() / "Documents" / "JarvisNotes"),
    "memory_db_path": str(MEMORY_DB_PATH),
    "prefix_saved_answer": False,    # Exact answer mode (default False = exact answer as written)
    "start_on_boot": False,
    "system_tray_minimize": True,
    "mic_index": None
}

def load_settings():
    settings = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                settings.update(saved)
        except Exception:
            pass
    # Ensure approved directories exist
    os.makedirs(settings["approved_workspace"], exist_ok=True)
    os.makedirs(settings["notes_dir"], exist_ok=True)
    if "memory_db_path" in settings:
        os.makedirs(Path(settings["memory_db_path"]).parent, exist_ok=True)
    return settings

def save_settings(settings):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Failed to save settings: {e}")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
