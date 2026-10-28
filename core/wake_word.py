import time
import threading
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from core.speech_to_text import enhance_audio, SAMPLE_RATE, CHANNELS

WAKE_PHRASES = [
    "hey jarvis", "jarvis", "a jarvis", "hai jarvis", "hi jarvis",
    "hello jarvis", "suno jarvis", "jarvis suno", "sun jarvis", "oye jarvis",
    "bhai jarvis", "ok jarvis", "okay jarvis", "travis", "service",
    "javis", "charvis", "chavis", "sarvice", "jervis", "harvest",
    "arvis", "service please", "hey travis", "hey service", "suno", "sun le",
    "जार्विस", "जारविस", "सुनो जार्विस", "सर्विस"
]

class WakeWordDetector:
    def __init__(self, tts_manager, stt_manager, on_wake=None, sensitivity=0.6):
        self.tts = tts_manager
        self.stt = stt_manager
        self.on_wake = on_wake
        self.sensitivity = sensitivity
        self.is_running = False
        self.is_paused = False
        self._thread = None
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 80
        self.recognizer.dynamic_energy_threshold = True

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_running = False

    def _loop(self):
        block_size = int(SAMPLE_RATE * 0.1)  # 100ms
        pre_roll = []
        pre_roll_limit = 5  # 500ms pre-roll to never clip initial syllable
        ambient_energy = 25.0

        while self.is_running:
            if self.is_paused or self.tts.is_speaking:
                time.sleep(0.2)
                continue

            try:
                mic_dev = getattr(self.stt, "device_index", None)
                with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype='int16', device=mic_dev) as stream:
                    buffer_frames = []
                    voice_detected = False
                    silence_count = 0
                    silence_limit = 7   # 700ms silence ends wake capture
                    max_blocks = 26     # Up to 2.6s for wake utterance

                    for block_idx in range(max_blocks):
                        if not self.is_running or self.is_paused or self.tts.is_speaking:
                            break

                        data, _ = stream.read(block_size)
                        energy = float(np.mean(np.abs(data)))

                        if not voice_detected:
                            # Dynamic ambient tracking
                            if energy < ambient_energy * 1.3:
                                ambient_energy = 0.92 * ambient_energy + 0.08 * energy

                            trigger_thresh = ambient_energy + max(ambient_energy * 0.14, 4.0)

                            pre_roll.append(data)
                            if len(pre_roll) > pre_roll_limit:
                                pre_roll.pop(0)

                            if energy > trigger_thresh:
                                voice_detected = True
                                buffer_frames.extend(pre_roll)
                        else:
                            buffer_frames.append(data)
                            sustain_thresh = ambient_energy + max(ambient_energy * 0.07, 2.0)
                            if energy > sustain_thresh:
                                silence_count = 0
                            else:
                                silence_count += 1
                                if silence_count >= silence_limit:
                                    break

                    if voice_detected and self.is_running and not self.is_paused and not self.tts.is_speaking:
                        audio_raw = np.concatenate(buffer_frames, axis=0).flatten()
                        # Apply studio DSP enhancer (AGC up to 120x, high pass, noise gating)
                        enhanced = enhance_audio(audio_raw, SAMPLE_RATE, ambient_energy)
                        if enhanced is not None:
                            audio_data = sr.AudioData(enhanced.tobytes(), SAMPLE_RATE, 2)
                            matched = False

                            # Multi-pass recognition for Hinglish, Hindi, and English variations
                            for lang in ["en-IN", "hi-IN", "en-US"]:
                                try:
                                    text = self.recognizer.recognize_google(audio_data, language=lang).lower()
                                    if any(phrase in text for phrase in WAKE_PHRASES):
                                        matched = True
                                        break
                                except (sr.UnknownValueError, sr.RequestError):
                                    continue
                                except Exception:
                                    break

                            if matched:
                                self.pause()  # Pause immediately so mic stream is released for command STT
                                if self.on_wake:
                                    self.on_wake()
            except Exception as e:
                time.sleep(0.3)

