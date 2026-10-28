
import asyncio
import edge_tts
import os
import ctypes

async def main():
    communicate = edge_tts.Communicate("Haan ji boss, Jarvis is online. Sab mast chal raha hai!", "en-IN-NeerjaNeural")
    await communicate.save("test_speech.mp3")
    print("MP3 saved, size:", os.path.getsize("test_speech.mp3"))
    mci = ctypes.windll.winmm.mciSendStringW
    mci("close jarvis_speech", None, 0, 0)
    res = mci('open "test_speech.mp3" type mpegvideo alias jarvis_speech', None, 0, 0)
    print("MCI open result:", res)
    mci("play jarvis_speech wait", None, 0, 0)
    mci("close jarvis_speech", None, 0, 0)
    print("Playback completed!")
    if os.path.exists("test_speech.mp3"):
        os.remove("test_speech.mp3")

if __name__ == "__main__":
    asyncio.run(main())
