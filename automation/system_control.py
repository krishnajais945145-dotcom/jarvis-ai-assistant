import ctypes
import datetime
from pycaw.pycaw import AudioUtilities

try:
    import screen_brightness_control as sbc
    SBC_AVAILABLE = True
except Exception:
    SBC_AVAILABLE = False

def get_date_time() -> tuple[str, str]:
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%I:%M %p")
    return date_str, time_str

def _get_volume_endpoint():
    speakers = AudioUtilities.GetSpeakers()
    if hasattr(speakers, "EndpointVolume"):
        return speakers.EndpointVolume
    # Fallback for older pycaw
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume
    interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))

def set_volume(level_percent: int) -> tuple[bool, str]:
    try:
        volume = _get_volume_endpoint()
        clamped = max(0, min(100, level_percent))
        volume.SetMasterVolumeLevelScalar(clamped / 100.0, None)
        return True, f"Volume set to {clamped}%."
    except Exception as e:
        return False, f"Failed to adjust volume: {str(e)}"

def change_volume(delta_percent: int) -> tuple[bool, str]:
    try:
        volume = _get_volume_endpoint()
        current = volume.GetMasterVolumeLevelScalar() * 100.0
        new_level = max(0, min(100, int(current + delta_percent)))
        volume.SetMasterVolumeLevelScalar(new_level / 100.0, None)
        return True, f"Volume adjusted to {new_level}%."
    except Exception as e:
        return False, f"Failed to change volume: {str(e)}"

def toggle_mute() -> tuple[bool, str]:
    try:
        volume = _get_volume_endpoint()
        is_muted = volume.GetMute()
        volume.SetMute(not is_muted, None)
        status = "muted" if not is_muted else "unmuted"
        return True, f"Audio is now {status}."
    except Exception as e:
        return False, f"Failed to toggle mute: {str(e)}"

def set_brightness(level_percent: int) -> tuple[bool, str]:
    if not SBC_AVAILABLE:
        return False, "Screen brightness control library not available."
    try:
        clamped = max(0, min(100, level_percent))
        sbc.set_brightness(clamped)
        return True, f"Brightness set to {clamped}%."
    except Exception as e:
        return False, f"Failed to set brightness: {str(e)}"

def change_brightness(delta_percent: int) -> tuple[bool, str]:
    if not SBC_AVAILABLE:
        return False, "Screen brightness control library not available."
    try:
        current = sbc.get_brightness()
        curr_val = current[0] if isinstance(current, list) and len(current) > 0 else 50
        new_val = max(5, min(100, curr_val + delta_percent))
        sbc.set_brightness(new_val)
        return True, f"Brightness changed to {new_val}%."
    except Exception as e:
        return False, f"Failed to adjust brightness: {str(e)}"

def lock_workstation() -> tuple[bool, str]:
    try:
        ctypes.windll.user32.LockWorkStation()
        return True, "Laptop screen locked."
    except Exception as e:
        return False, f"Failed to lock workstation: {str(e)}"
