import threading
from PIL import Image, ImageDraw
import pystray

def create_jarvis_icon():
    # Generate a sleek cyan-ring circular icon
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, 60, 60), outline=(0, 229, 255, 255), width=4)
    draw.ellipse((16, 16, 48, 48), outline=(0, 136, 204, 255), width=3)
    draw.ellipse((26, 26, 38, 38), fill=(0, 229, 255, 255))
    return image

class SystemTrayManager:
    def __init__(self, on_show=None, on_pause=None, on_resume=None, on_exit=None):
        self.on_show = on_show
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.on_exit = on_exit
        self.icon = None
        self._thread = None

    def start(self):
        icon_img = create_jarvis_icon()
        menu = pystray.Menu(
            pystray.MenuItem("Open JARVIS", lambda: self.on_show() if self.on_show else None),
            pystray.MenuItem("Pause Listening", lambda: self.on_pause() if self.on_pause else None),
            pystray.MenuItem("Resume Listening", lambda: self.on_resume() if self.on_resume else None),
            pystray.MenuItem("Exit", lambda: self.on_exit() if self.on_exit else None)
        )
        self.icon = pystray.Icon("JARVIS", icon_img, "JARVIS AI Assistant", menu)
        self._thread = threading.Thread(target=self.icon.run, daemon=True)
        self._thread.start()

    def stop(self):
        if self.icon:
            self.icon.stop()
