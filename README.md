# 🤖 J.A.R.V.I.S. — Personal AI Voice Assistant for Windows

An autonomous, sci-fi inspired personal AI voice assistant for **Windows 10/11**. Features hands-free **"Hey Jarvis"** wake-word detection, **Hinglish/Hindi/English** bilingual speech understanding, an expressive female voice with witty and mildly sarcastic personality, real Windows desktop automation, and an animated Arc Reactor HUD interface.

---

## 🌟 Key Capabilities

1. **Wake Word ("Hey Jarvis")**:
   - Hands-free background listener with local energy detection to minimize CPU and battery usage.
   - Prevents self-triggering while JARVIS is speaking.
   - Pause/Resume anytime directly from UI or System Tray.

2. **Hinglish, Hindi & English Natural Language Processing**:
   - Handles mixed Hinglish (*"Chrome kholo aur YouTube pe Arijit Singh ke songs chala do"*), pure Hindi (*"आज का समय क्या है?"*), and English.
   - Contextual understanding for follow-up commands (*"Isko band karo"*, *"Jo abhi bola tha woh repeat karo"*).
   - Auto-detects your spoken language and replies in the matched tongue.

3. **Expressive Female Voice & Witty Persona**:
   - High-quality natural Indian female TTS (`en-IN-NeerjaNeural`, `hi-IN-SwaraNeural`) via `edge-tts`.
   - 100% offline fallback voice via Windows SAPI5 (`pyttsx3`).
   - Friendly sarcasm and witty remarks (*"Code mein error hai? Surprise-surprise! Chalo milke theek karte hain"*).
   - Instant interruptibility via the **Stop** button.

4. **Real Windows Laptop Automation**:
   - **Apps**: Chrome, Microsoft Edge, VS Code, Notepad, Calculator, File Explorer.
   - **System Controls**: Screen brightness adjustment, volume slider/mute/unmute (via `pycaw`), workstation lock (`Win+L`).
   - **Web & Media**: YouTube video playback, Google web search, GitHub navigation.
   - **File Operations**: Safe folder creation (*"College Projects"*), notes, text files strictly restricted to approved user folders.
   - **Persistent Reminders**: Saved locally to JSON; runs in background and alerts you with audio chimes.
   - **Code Diagnostics**: Explains SyntaxError, IndentationError, ModuleNotFoundError in simple Hinglish.

5. **Futuristic Sci-Fi Desktop GUI & System Tray**:
   - CustomTkinter dark theme with cyan/blue neon accents.
   - Animated glowing **Arc Reactor Core** with dynamic pulse and spinning rings.
   - Conversation transcript bubbles, text-input fallback, quick command buttons.
   - Minimizes to Windows System Tray (`pystray`).

6. **JARVIS Companion for Realme 10 Pro (Wi-Fi Calling & Contacts)**:
   - Standalone Android app in `companion_app/` paired securely over local Wi-Fi.
   - Requests normal runtime Android permissions (`READ_CONTACTS`, `CALL_PHONE`).
   - Voice commands like *"Jarvis, mummy ko call lagao"* find contacts and ask for confirmation before dialing.
   - Ready-to-install debug APK available in `dist/JARVIS_Companion.apk`.

---

## 🚀 Quick Launch (Double Click)

You have two launch options:

### Option 1: Desktop Shortcut (Easiest)
- Double-click the **`JARVIS AI Assistant`** shortcut placed on your Windows Desktop!

### Option 2: 1-Click Batch Launcher
- Double-click **`run_jarvis.bat`** in the project folder.

### Option 3: Standalone Executable (.exe)
- Located at:
  ```
  dist\JARVIS\JARVIS.exe
  ```

---

## ⚙️ Configuration & Setup

### 1. Requirements & Dependencies
All dependencies are pre-installed in your environment. If you ever move the project or reinstall:
```powershell
pip install -r requirements.txt
```

### 2. Optional: Cloud AI Brain (Google Gemini)
JARVIS works **completely offline** for laptop controls, reminders, jokes, and system actions. If you'd like deep conversational reasoning, explanations, and translation:
1. Copy `.env.example` to `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Open `.env` and enter your free Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_actual_api_key_here
   ```
3. Alternatively, click **⚙ Settings** inside the JARVIS app to set the key graphically!

---

## 🎙 Spoken Command Cheat-Sheet (30+ Tested Commands)

| Category | Spoken Command (Hinglish / Hindi / English) | What JARVIS Does |
|---|---|---|
| **Media Playback** | *"Jarvis, Chrome kholo aur YouTube pe Arijit Singh ke songs chala do."* | Opens YouTube search results and starts video |
| **Brightness Down** | *"Mere laptop ki brightness thodi kam kar do."* | Lowers screen brightness by 15% |
| **Brightness Up** | *"Brightness badha do"* | Increases screen brightness by 15% |
| **Volume Control** | *"Volume 50 percent set karo"* / *"Awaaz kam karo"* | Adjusts master Windows volume |
| **Mute** | *"Audio mute kar do"* | Toggles system sound mute |
| **Date & Time** | *"Jarvis, aaj ka date aur time batao."* | Announces formatted date and time |
| **Reminders** | *"Kal subah 8 baje mujhe college ke liye remind kar dena."* | Saves persistent local reminder |
| **Coding Debug** | *"Yaar, mera code run nahi ho raha, check karo kya problem hai."* | Diagnoses code issues in Hinglish |
| **VS Code Launcher** | *"Pehle VS Code kholo, phir mera project open kar do."* | Opens VS Code in workspace folder |
| **Humor / Joke** | *"Aaj mood nahi hai coding ka, kuch funny batao."* | Delivers witty programmer joke |
| **Folder Creation** | *"Naya folder bana ke do aur iska naam College Projects rakh do."* | Safely creates folder in `Documents` |
| **App Launch** | *"Notepad kholo"* / *"Calculator open kar do"* | Launches verified allowed application |
| **Contextual Close** | *"Isko band karo"* | Resolves recent app and closes safely |
| **Contextual Repeat**| *"Jo abhi bola tha woh repeat karo."* | Repeats previous spoken answer |
| **Gratitude** | *"Thank you Jarvis, bohot badhiya kaam kiya."* | Friendly, witty response |
| **Web Search** | *"Google pe dhoondo best python libraries"* | Searches Google in default browser |
| **System Lock** | *"Laptop lock kar do"* | Instantly locks Windows screen |
| **Pure Hindi** | *"आज का समय क्या है?"* / *"नमस्ते जार्वis, कैसी हो?"* | Responds in native Hindi |
| **Pure English** | *"Open Google Chrome please"* / *"What time is it?"* | Responds in natural English |

---

## 🧪 Automated Test Verification

Run the automated 32-command test suite anytime:
```powershell
python tests/test_suite.py
```
**Verification Result**: **32 / 32 Passed (100% Pass Rate)**

---

## 🛠 Troubleshooting & Tips

1. **Microphone not picking up?**
   - Click the **🎙 Speak** button on the bottom bar to test manual input.
   - Verify Windows Settings > Privacy & Security > Microphone permissions are enabled.
   - Ensure your microphone is configured as the default Windows recording device.

2. **Offline Mode vs Online Mode**:
   - Laptop controls (Volume, Brightness, Apps, Files, Lock, Reminders) work **100% offline**.
   - Edge-TTS uses Microsoft's high-speed speech cloud for ultra-natural voice. If offline, JARVIS automatically falls back to Windows native SAPI5 speech!

3. **Background Listening & Battery Saving**:
   - If watching movies or on a call, click **"Pause Wake Word"** or use the System Tray menu to prevent accidental activations.
