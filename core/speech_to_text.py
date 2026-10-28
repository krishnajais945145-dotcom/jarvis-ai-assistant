import os
import io
import time
import numpy as np
import sounddevice as sd
import speech_recognition as sr

SAMPLE_RATE = 16000
CHANNELS = 1

def enhance_audio(audio_array: np.ndarray, sample_rate: int = 16000, noise_floor: float = 25.0) -> np.ndarray:
    """
    Studio-grade DSP audio pipeline for far-field, distant, and whispered speech:
    1. DC offset removal
    2. Sub-bass high-pass filter (~80-100Hz) to eliminate AC hum, fan rumble & mic drift
    3. Stationary noise floor soft-gating to attenuate background room hiss
    4. Two-stage Automatic Gain Control (AGC) boosting soft/distant speech up to 120x
    5. Soft-knee dynamic limiter (tanh compression) to prevent clipping/distortion
    """
    if audio_array is None or len(audio_array) == 0:
        return None

    data = audio_array.astype(np.float32)

    # 1. DC offset removal
    data = data - np.mean(data)

    # 2. Sub-bass high-pass filter (~80-100Hz cutoff via running average subtraction)
    # 160 samples at 16kHz corresponds to 10ms (100Hz)
    window_size = min(160, max(len(data) // 6, 4))
    if len(data) >= window_size and window_size > 0:
        cumsum = np.cumsum(np.insert(data, 0, 0))
        moving_avg = (cumsum[window_size:] - cumsum[:-window_size]) / window_size
        pad_left = window_size // 2
        pad_right = len(data) - len(moving_avg) - pad_left
        avg_padded = np.pad(moving_avg, (pad_left, pad_right), mode='edge')
        data = data - avg_padded

    # 3. Ambient noise floor soft-gating
    # Gently attenuate stationary room hiss in silent portions without cutting voice syllables
    abs_data = np.abs(data)
    gate_mask = abs_data < (noise_floor * 0.85)
    data[gate_mask] = data[gate_mask] * 0.65

    # 4. Two-Stage AGC (Automatic Gain Control)
    # Estimate speech amplitude using the 99.2 percentile to discard stray pop clicks
    top_amp = float(np.percentile(abs_data, 99.2))
    if top_amp < 6.0:
        top_amp = float(np.max(abs_data))

    if top_amp < 4.0:
        # Complete digital silence or disconnected mic
        return None

    target_peak = 25000.0
    boost_factor = target_peak / max(top_amp, 1.0)
    # Allow generous gain boost up to 120.0x for distant or whispered speech
    boost_factor = min(boost_factor, 120.0)
    data = data * boost_factor

    # 5. Soft-knee dynamic limiter (smooth compression for peaks above 28,000)
    limit = 28000.0
    over = np.abs(data) > limit
    if np.any(over):
        excess = np.abs(data) - limit
        scale = limit + (32700.0 - limit) * np.tanh(excess / 6000.0)
        data = np.where(over, np.sign(data) * scale, data)

    return np.clip(data, -32768, 32767).astype(np.int16)

class SpeechToTextManager:
    def __init__(self, device_index=None):
        self.device_index = device_index
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 80
        self.recognizer.dynamic_energy_threshold = True

    def record_phrase(self, max_duration=9.0, silence_limit=1.8, initial_timeout=5.0):
        """
        Record audio with dynamic far-field sensitivity, pre-speech buffering,
        smart silence hysteresis, and studio-grade DSP enhancement.
        """
        block_size = int(SAMPLE_RATE * 0.1)  # 100ms blocks
        frames = []
        pre_roll = []  # Ring buffer to preserve initial consonant syllables (~600ms)
        pre_roll_limit = 6

        silence_blocks = 0
        max_silence_blocks = int(silence_limit / 0.1)
        max_blocks = int(max_duration / 0.1)
        initial_timeout_blocks = int(initial_timeout / 0.1)

        has_spoken = False
        noise_floor = 25.0

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype='int16',
                device=self.device_index
            ) as stream:
                for block_idx in range(max_blocks):
                    data, _ = stream.read(block_size)
                    flat_data = data.flatten()
                    energy = float(np.mean(np.abs(flat_data)))

                    if not has_spoken:
                        # Adapt noise floor during initial quiet period
                        if block_idx < 3:
                            noise_floor = 0.7 * noise_floor + 0.3 * energy if block_idx > 0 else energy
                        elif energy < noise_floor * 1.25:
                            noise_floor = 0.9 * noise_floor + 0.1 * energy

                        # Dynamic speech threshold: sensitive to soft speech & far-field
                        trigger_delta = max(noise_floor * 0.16, 5.0)
                        speech_threshold = noise_floor + trigger_delta

                        pre_roll.append(data)
                        if len(pre_roll) > pre_roll_limit:
                            pre_roll.pop(0)

                        if energy > speech_threshold:
                            has_spoken = True
                            frames.extend(pre_roll)
                            silence_blocks = 0
                        else:
                            if block_idx >= initial_timeout_blocks:
                                break
                    else:
                        frames.append(data)
                        # Hysteresis for sustaining speech: lower threshold so soft continuous speech isn't cut off
                        sustain_delta = max(noise_floor * 0.08, 2.5)
                        if energy > (noise_floor + sustain_delta):
                            silence_blocks = 0
                        else:
                            silence_blocks += 1
                            if silence_blocks >= max_silence_blocks:
                                break
        except Exception as e:
            print(f"[STT] Microphone recording error: {e}")
            return None

        if not frames:
            return None

        audio_raw = np.concatenate(frames, axis=0).flatten()
        enhanced = enhance_audio(audio_raw, SAMPLE_RATE, noise_floor)
        if enhanced is None:
            return None

        audio_bytes = enhanced.tobytes()
        return sr.AudioData(audio_bytes, SAMPLE_RATE, 2)

    def recognize_audio(self, audio_data: sr.AudioData, primary_lang="en-IN") -> str:
        """
        Transcribe audio using multi-pass recognition:
        Pass 1: Indian English / Hinglish (en-IN)
        Pass 2: Hindi (hi-IN)
        Pass 3: General English (en-US fallback)
        """
        if audio_data is None:
            return ""

        # Pass 1: Indian English / Hinglish
        try:
            text = self.recognizer.recognize_google(audio_data, language=primary_lang)
            if text and len(text.strip()) > 0:
                return text.strip()
        except sr.UnknownValueError:
            pass
        except sr.RequestError as re:
            print(f"[STT] Google STT network error on pass 1 ({primary_lang}): {re}")
        except Exception as e:
            print(f"[STT] Google recognition pass 1 note: {e}")

        # Pass 2: Hindi (hi-IN)
        try:
            text = self.recognizer.recognize_google(audio_data, language="hi-IN")
            if text and len(text.strip()) > 0:
                return text.strip()
        except (sr.UnknownValueError, sr.RequestError):
            pass
        except Exception:
            pass

        # Pass 3: General English (en-US fallback)
        try:
            text = self.recognizer.recognize_google(audio_data, language="en-US")
            if text and len(text.strip()) > 0:
                return text.strip()
        except Exception:
            pass

        return ""
