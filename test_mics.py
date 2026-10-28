import sounddevice as sd
import numpy as np

devices = sd.query_devices()
print("Total audio devices found:", len(devices))
for idx, d in enumerate(devices):
    if d['max_input_channels'] > 0:
        try:
            rec = sd.rec(int(16000 * 0.4), samplerate=16000, channels=1, dtype='int16', device=idx)
            sd.wait()
            mean_e = np.mean(np.abs(rec))
            max_a = np.max(np.abs(rec))
            print(f"Device {idx:02d} [{d['name'][:35]} | hostapi: {d['hostapi']}] -> mean: {mean_e:.1f}, max: {max_a}")
        except Exception as e:
            print(f"Device {idx:02d} error: {e}")
