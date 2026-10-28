import os
import sys
import threading
import time
import winsound
import ctypes
import multiprocessing
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import load_settings, save_settings
from core.safety import SafetyManager
from core.text_to_speech import TextToSpeechManager
from core.speech_to_text import SpeechToTextManager
from core.wake_word import WakeWordDetector
from core.brain import JarvisBrain
from automation.reminders import ReminderManager
from ui.jarvis_gui import JarvisGUI
from ui.tray_icon import SystemTrayManager

class JarvisApp:
    def __init__(self):
        self.settings = load_settings()
        self.safety = SafetyManager()

        # Initialize TTS
        self.tts = TextToSpeechManager(
            voice_engine=self.settings.get("voice_engine", "edge-tts"),
            voice_female_en=self.settings.get("voice_female_en", "en-IN-NeerjaNeural"),
            voice_female_hi=self.settings.get("voice_female_hi", "hi-IN-SwaraNeural")
        )

        # Initialize STT with AGC
        self.stt = SpeechToTextManager(device_index=self.settings.get("mic_index"))
        self.is_recording = False
        self._user_paused_wake = False

        # Initialize Reminders with callback
        self.reminders = ReminderManager(on_reminder_trigger=self.handle_reminder_alert)

        # Initialize Brain
        self.brain = JarvisBrain(reminder_manager=self.reminders, config=self.settings)

        # Initialize GUI
        self.gui = JarvisGUI(
            on_command_submit=self.handle_user_text_command,
            on_mic_click=self.handle_manual_mic_trigger,
            on_stop_click=self.handle_stop,
            on_pause_toggle=self.handle_pause_wake_word,
            on_save_settings=self.handle_settings_update,
            current_settings=self.settings,
            memory_manager=self.brain.memory_mgr,
            on_whatsapp_open=lambda: self.execute_command("Jarvis WhatsApp kholo"),
            on_whatsapp_cancel=lambda: self.execute_command("WhatsApp cancel karo"),
            on_whatsapp_confirm=lambda: self.execute_command("Haan bhejo"),
            companion_manager=self.brain.companion_mgr
        )
        self.brain.on_memory_ui_trigger = self.gui.open_memory_modal
        # Connect real-time WhatsApp status notifications to GUI
        self.brain.whatsapp_mgr.on_status_change = lambda st, msg: self.gui.after(0, lambda: self.gui.update_whatsapp_status(st, msg))
        # Connect Phone Companion status notifications to GUI
        def _on_companion_status(st, msg):
            self.gui.update_phone_status(st, msg)
            if "CONNECT" in (st or "").upper():
                self.gui.append_transcript("System", f"📱 Phone Companion: {msg}")
        self.brain.companion_mgr.on_status_change = lambda st, msg: self.gui.after(0, lambda: _on_companion_status(st, msg))

        # Initialize Wake Word Detector
        self.wake_detector = WakeWordDetector(
            tts_manager=self.tts,
            stt_manager=self.stt,
            on_wake=self.handle_wake_word_triggered,
            sensitivity=self.settings.get("wake_word_sensitivity", 0.6)
        )

        # Initialize System Tray
        self.tray = SystemTrayManager(
            on_show=self.show_window,
            on_pause=lambda: self.handle_pause_wake_word(True),
            on_resume=lambda: self.handle_pause_wake_word(False),
            on_exit=self.quit_app
        )

    def start(self):
        # Ensure window is visible and focused
        self.gui.deiconify()
        self.gui.lift()
        self.gui.focus_force()

        # Start Phone Companion Wi-Fi bridge
        self.brain.companion_mgr.start()

        # Start Wake Word detector in background
        self.wake_detector.start()

        # Start System Tray icon
        if self.settings.get("system_tray_minimize", True):
            self.tray.start()

        # Speak greeting in background
        threading.Thread(
            target=lambda: self.tts.speak("Jarvis online boss. How can I help you today?"),
            daemon=True
        ).start()

        # Run GUI loop on main thread
        self.gui.mainloop()

    def handle_wake_word_triggered(self):
        """Called automatically when user says 'Hey Jarvis'."""
        if self.tts.is_speaking or self.is_recording:
            return

        def _workflow():
            self.is_recording = True
            self.wake_detector.pause()
            try:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    time.sleep(0.35)  # Wait for chime to stop so it doesn't feed back into mic
                except Exception:
                    pass

                self.gui.set_status("LISTENING")
                audio_data = self.stt.record_phrase(max_duration=9.0, silence_limit=1.8, initial_timeout=5.0)
                if not audio_data:
                    self.gui.set_status("IDLE")
                    return

                self.gui.set_status("THINKING")
                recognized_text = self.stt.recognize_audio(audio_data)
                if not recognized_text:
                    self.gui.append_transcript("System", "Could not clearly capture voice. Try speaking closer to the mic.")
                    self.gui.set_status("IDLE")
                    return

                self.gui.append_transcript("User", recognized_text)
                self.execute_command(recognized_text)
            finally:
                self.is_recording = False
                if not getattr(self, "_user_paused_wake", False):
                    self.wake_detector.resume()

        threading.Thread(target=_workflow, daemon=True).start()

    def handle_manual_mic_trigger(self):
        """Called when user clicks the 🎙 Speak button."""
        if self.tts.is_speaking or self.is_recording:
            return

        def _workflow():
            self.is_recording = True
            self.wake_detector.pause()
            try:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                    time.sleep(0.35)  # Wait for chime to stop so it doesn't feed back into mic
                except Exception:
                    pass

                self.gui.set_status("LISTENING")
                audio_data = self.stt.record_phrase(max_duration=9.0, silence_limit=1.8, initial_timeout=5.0)
                if not audio_data:
                    self.gui.append_transcript("System", "No speech detected. Check microphone volume.")
                    self.gui.set_status("IDLE")
                    return

                self.gui.set_status("THINKING")
                recognized_text = self.stt.recognize_audio(audio_data)
                if not recognized_text:
                    self.gui.append_transcript("System", "Awaaz saaf nahi aayi boss, please thoda clear boliye!")
                    self.tts.speak("Awaaz saaf nahi aayi boss, please dobara boliye.")
                    self.gui.set_status("IDLE")
                    return

                self.gui.append_transcript("User", recognized_text)
                self.execute_command(recognized_text)
            finally:
                self.is_recording = False
                if not getattr(self, "_user_paused_wake", False):
                    self.wake_detector.resume()

        threading.Thread(target=_workflow, daemon=True).start()

    def handle_user_text_command(self, text: str):
        self.execute_command(text)

    def execute_command(self, text: str):
        self.gui.set_status("THINKING")
        response = self.brain.process_command(text)

        self.gui.append_transcript("JARVIS", response)
        self.gui.set_status("SPEAKING")
        self.tts.speak(response, on_finish=lambda: self.gui.set_status("IDLE"))

    def handle_stop(self):
        self.tts.stop_speaking()
        self.gui.set_status("IDLE")

    def handle_pause_wake_word(self, is_paused: bool):
        self._user_paused_wake = is_paused
        if is_paused:
            self.wake_detector.pause()
        else:
            self.wake_detector.resume()

    def handle_settings_update(self, new_settings: dict):
        self.settings.update(new_settings)
        save_settings(self.settings)
        if "mic_index" in new_settings:
            self.stt.device_index = new_settings["mic_index"]
        if "wake_word_sensitivity" in new_settings:
            self.wake_detector.sensitivity = new_settings["wake_word_sensitivity"]
        if "voice_engine" in new_settings:
            self.tts.voice_engine = new_settings["voice_engine"]
        if "gemini_key" in new_settings and new_settings["gemini_key"]:
            key = new_settings["gemini_key"].strip()
            ok = self.brain._init_llm(key)
            env_file = Path(__file__).resolve().parent / ".env"
            try:
                with open(env_file, "w", encoding="utf-8") as f:
                    f.write(f"GEMINI_API_KEY={key}\n")
            except Exception:
                pass
            if ok:
                msg = "Google Gemini 1.5 Flash personal AI brain connected successfully, boss!"
                self.gui.append_transcript("JARVIS", msg)
                self.tts.speak("Personal Gemini 1.5 Flash connected successfully boss! Now I can answer anything.")

    def handle_reminder_alert(self, message: str):
        alert_text = f"Boss, reminder alert: {message}!"
        if hasattr(self, "gui") and self.gui:
            try:
                self.gui.append_transcript("JARVIS", alert_text)
            except Exception:
                pass

    def show_window(self):
        self.gui.deiconify()
        self.gui.lift()
        self.gui.focus_force()

    def quit_app(self):
        self.wake_detector.stop()
        self.brain.companion_mgr.stop()
        self.tts.stop_speaking()
        self.tray.stop()
        self.gui.destroy()
        sys.exit(0)

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Enforce clean single-instance: Terminate any stale python processes running app.py
    curr_pid = os.getpid()
    try:
        import psutil
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if p.info['pid'] != curr_pid and p.info['name'] and 'python' in p.info['name'].lower():
                    cmd = ' '.join(p.info['cmdline'] or []).lower()
                    if 'app.py' in cmd:
                        p.kill()
            except Exception:
                pass
    except Exception:
        pass

    app = JarvisApp()
    app.start()
