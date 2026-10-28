import os
import time
import uuid
import ctypes
import asyncio
import threading
from pathlib import Path

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

TEMP_AUDIO_DIR = Path.home() / ".jarvis_cache" / "tts"


TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

class TextToSpeechManager:
    def __init__(self, voice_engine="edge-tts", voice_female_en="en-IN-NeerjaNeural", voice_female_hi="hi-IN-SwaraNeural"):
        self.voice_engine = voice_engine
        self.voice_female_en = voice_female_en
        self.voice_female_hi = voice_female_hi
        self.is_speaking = False
        self._stop_event = threading.Event()
        self._current_alias = None
        self._winmm = ctypes.windll.winmm
        self._lock = threading.Lock()

        # Offline engine setup
        self.pyttsx_engine = None
        if PYTTSX3_AVAILABLE:
            try:
                self.pyttsx_engine = pyttsx3.init()
                voices = self.pyttsx_engine.getProperty('voices')
                for v in voices:
                    if "zira" in v.name.lower() or "female" in v.name.lower():
                        self.pyttsx_engine.setProperty('voice', v.id)
                        break
            except Exception as e:
                print(f"[TTS] pyttsx3 init error: {e}")

    def stop_speaking(self):
        """Immediately interrupt and stop any ongoing speech output."""
        self._stop_event.set()
        with self._lock:
            if self._current_alias:
                try:
                    self._winmm.mciSendStringW(f'stop {self._current_alias}', None, 0, 0)
                    self._winmm.mciSendStringW(f'close {self._current_alias}', None, 0, 0)
                except Exception:
                    pass
                self._current_alias = None
        self.is_speaking = False

    def _clean_text_for_speech(self, text: str) -> str:
        """Strip markdown symbols, asterisks, URLs, and noisy formatting for clean phonetics."""
        import re
        t = re.sub(r'[*_#`~>\[\]\(\)]', ' ', text)
        t = re.sub(r'https?://\S+', ' link ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def _detect_script(self, text: str) -> str:
        """Detect whether text is Hindi/Hinglish or Pure English."""
        import re
        if any('\u0900' <= char <= '\u097F' for char in text):
            return "hindi"

        hinglish_words = {
            "hai", "hain", "ho", "hoon", "hatao", "haan", "nahi", "nahin", "karo", "kardo",
            "khol", "kholo", "batao", "chala", "chalao", "mera", "meri", "mere", "aap", "aapke",
            "aapka", "kya", "kyu", "kyun", "kaise", "thoda", "baat", "diya", "dekh", "liye",
            "mein", "me", "se", "ko", "par", "pe", "bohot", "achha", "shukar", "manao",
            "aaj", "samay", "waqt", "kaam", "mat", "raha", "rahi", "gaya", "gayi", "karna",
            "sunao", "suno", "theek", "shanti", "bilkul", "badha", "kam", "der", "kal", "karungi", "karunga"
        }
        tokens = set(re.findall(r'\b\w+\b', text.lower()))
        if tokens.intersection(hinglish_words):
            return "hinglish"
        return "english"

    def speak(self, text: str, on_start=None, on_finish=None, blocking=False):
        """Speak the provided text asynchronously or blocking."""
        if not text or not text.strip():
            return

        clean_text = self._clean_text_for_speech(text)
        if not clean_text:
            return

        def _worker():
            self.stop_speaking()
            self._stop_event.clear()
            self.is_speaking = True
            if on_start:
                try:
                    on_start()
                except Exception:
                    pass

            played = False
            # Try edge-tts first if enabled
            if self.voice_engine == "edge-tts" and EDGE_TTS_AVAILABLE:
                try:
                    script = self._detect_script(clean_text)
                    # For Hindi AND Hinglish, use native Hindi neural voice (Swara) for natural Indian pronunciation!
                    chosen_voice = self.voice_female_hi if script in ["hindi", "hinglish"] else self.voice_female_en
                    filename = f"jarvis_voice_{uuid.uuid4().hex[:8]}.mp3"
                    filepath = str(TEMP_AUDIO_DIR / filename)

                    async def _generate():
                        comm = edge_tts.Communicate(clean_text, chosen_voice, rate="+3%")
                        await comm.save(filepath)

                    asyncio.run(_generate())

                    if not self._stop_event.is_set() and os.path.exists(filepath):
                        alias = f"speech_{uuid.uuid4().hex[:6]}"
                        with self._lock:
                            self._current_alias = alias
                        
                        self._winmm.mciSendStringW(f'open "{filepath}" type mpegvideo alias {alias}', None, 0, 0)
                        self._winmm.mciSendStringW(f'play {alias} wait', None, 0, 0)
                        with self._lock:
                            if self._current_alias == alias:
                                self._winmm.mciSendStringW(f'close {alias}', None, 0, 0)
                                self._current_alias = None
                        
                        try:
                            os.remove(filepath)
                        except Exception:
                            pass
                        played = True
                except Exception as e:
                    print(f"[TTS] edge-tts error, falling back to pyttsx3: {e}")

            # Offline SAPI5 Fallback
            if not played and not self._stop_event.is_set():
                if self.pyttsx_engine:
                    try:
                        self.pyttsx_engine.say(text)
                        self.pyttsx_engine.runAndWait()
                        played = True
                    except Exception as err:
                        print(f"[TTS] pyttsx3 playback failed: {err}")

            self.is_speaking = False
            if on_finish:
                try:
                    on_finish()
                except Exception:
                    pass

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        if blocking:
            t.join()
