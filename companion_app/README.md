# 📱 JARVIS Companion — Android App for Realme 10 Pro

Welcome to **JARVIS Companion**! This Android application bridges your **Realme 10 Pro** smartphone with your **JARVIS Windows Assistant** on your laptop over the same local Wi-Fi network.

---

## 🎯 What This App Does

1. **Local Wi-Fi Pairing**: Securely connects your Realme 10 Pro to JARVIS on your laptop using an authenticated 6-digit PIN.
2. **Android Permission Prompts**: Requests `READ_CONTACTS` and `CALL_PHONE` permissions through standard Android system dialogs.
3. **Voice-Activated Contact Calling**:
   - When you say to JARVIS on your laptop:
     > *"Jarvis, mummy ko call lagao"*
   - JARVIS looks up "Mummy" across your phone's contacts via Wi-Fi.
   - JARVIS confirms:
     > *"Boss, Mummy ka number mil gaya hai: +91 98765 43210. Kya main call lagaoon?"*
   - You reply:
     > *"Haan call lagao"* (or *"Cancel"*)
   - JARVIS commands the Companion app to place the direct call via Android Telecom.
4. **Live Activity Console**: Shows real-time connection status, contact lookups, and call logs.

---

## 📦 Ready-to-Install APK Path

The debug APK has already been compiled:

- **Dist Folder**:
  ```
  dist/JARVIS_Companion.apk
  ```
- **Android Studio Output Folder**:
  ```
  companion_app/app/build/outputs/apk/debug/app-debug.apk
  ```

---

## 📲 How to Install on Your Realme 10 Pro

### Method 1: USB Cable (Fastest)
1. Connect your Realme 10 Pro to your laptop using a USB-C cable.
2. On your phone, select **File Transfer / Android Auto**.
3. Copy `dist\JARVIS_Companion.apk` into your phone's **Downloads** folder.
4. On your Realme 10 Pro, open the **File Manager** (Files app) -> **Downloads** -> tap `JARVIS_Companion.apk`.
5. Tap **Install** (if prompted, allow *"Install unknown apps"* for File Manager).

### Method 2: Google Drive / WhatsApp
1. Send `JARVIS_Companion.apk` to yourself on WhatsApp Web or upload to Google Drive.
2. On your Realme 10 Pro, download and tap the file to install.

---

## 🔗 How to Connect & Pair Over Wi-Fi

1. **Connect both devices to the same Wi-Fi router / mobile hotspot**.
2. **Start JARVIS on Windows**:
   - Double-click `run_jarvis.bat` or your desktop shortcut.
   - Your laptop's local IP is automatically detected (e.g. `192.168.137.183`).
   - Default Pairing PIN is: `742918`.
3. **Open JARVIS Companion on your Realme 10 Pro**:
   - Tap **Grant Permissions** when prompted for Contacts and Phone Calls.
   - Enter your Laptop IP: `192.168.137.183` (or whatever IP is displayed in JARVIS)
   - Port: `8765`
   - PIN: `742918`
   - Tap **CONNECT TO JARVIS**.
   - The status badge will change to **ONLINE & PAIRED** in neon green!

---

## 🗣️ Voice Commands to Try

| You Say | JARVIS Response & Action |
|---|---|
| *"Jarvis, mummy ko call lagao"* | JARVIS finds Mummy's number and asks: *"Boss, Mummy ka number mil gaya hai: +91 98765 43210. Kya main call lagaoon?"* |
| *"Haan call lagao"* (or *"Yes"*) | JARVIS says: *"Calling Mummy now boss!"* and dials the number on your phone. |
| *"Cancel"* (or *"Nahi"*) | JARVIS says: *"Cancelled boss! Mummy ko call nahi lagayi gayi."* |
| *"Phone status kya hai"* | JARVIS reports whether your phone is paired and online. |

---

## 🛠️ Opening the Project in Android Studio

If you want to view or modify the Android project in Android Studio:
1. Open **Android Studio**.
2. Click **File -> Open**.
3. Select the `companion_app` folder in the project.
4. Let Gradle sync. You can press **Run (Shift+F10)** with your Android device connected via USB Debugging.

---

## 🏗️ Rebuilding the APK from Command Line

To rebuild the APK at any time from your laptop:
```cmd
cd companion_app
gradlew.bat assembleDebug
```
The output APK is generated at `companion_app\app\build\outputs\apk\debug\app-debug.apk`.
