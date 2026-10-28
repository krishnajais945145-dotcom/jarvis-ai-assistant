import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.brain import JarvisBrain
from core.safety import SafetyManager
from automation.reminders import ReminderManager

def run_jarvis_test_suite():
    print("=" * 65)
    print("      J.A.R.V.I.S. AUTOMATED 32-COMMAND TEST SUITE")
    print("=" * 65)

    reminders = ReminderManager()
    brain = JarvisBrain(reminder_manager=reminders)
    safety = SafetyManager()

    test_cases = [
        # --- Hinglish Commands ---
        {"cmd": "Jarvis, Chrome kholo aur YouTube pe Arijit Singh ke songs chala do.", "category": "Hinglish Multi-Action", "check": lambda r: "youtube" in r.lower() and "arijit" in r.lower()},
        {"cmd": "Mere laptop ki brightness thodi kam kar do.", "category": "Hinglish Brightness Down", "check": lambda r: "brightness" in r.lower() or "kam" in r.lower()},
        {"cmd": "Brightness badha do", "category": "Hinglish Brightness Up", "check": lambda r: "brightness" in r.lower() or "badha" in r.lower()},
        {"cmd": "Volume 50 percent set karo", "category": "Hinglish Volume Set", "check": lambda r: "50" in r or "volume" in r.lower()},
        {"cmd": "Awaaz thodi kam karo", "category": "Hinglish Volume Down", "check": lambda r: "volume" in r.lower() or "awaaz" in r.lower()},
        {"cmd": "Audio mute kar do", "category": "Hinglish Mute", "check": lambda r: "mute" in r.lower()},
        {"cmd": "Jarvis, aaj ka date aur time batao.", "category": "Hinglish Date & Time", "check": lambda r: "time" in r.lower() or "aaj" in r.lower()},
        {"cmd": "Kal subah 8 baje mujhe college ke liye remind kar dena.", "category": "Hinglish Reminder", "check": lambda r: "reminder" in r.lower() or "alert" in r.lower()},
        {"cmd": "Yaar, mera code run nahi ho raha, check karo kya problem hai.", "category": "Hinglish Code Debugging", "check": lambda r: "error" in r.lower() or "bug" in r.lower() or "code" in r.lower()},
        {"cmd": "Pehle VS Code kholo, phir mera project open kar do.", "category": "Hinglish VS Code Launcher", "check": lambda r: "code" in r.lower() or "open" in r.lower()},
        {"cmd": "Aaj mood nahi hai coding ka, kuch funny batao.", "category": "Hinglish Humor & Joke", "check": lambda r: any(k in r.lower() for k in ["developer", "programmer", "404", "coffee", "human", "coding", "bug", "stack overflow", "joke"])},
        {"cmd": "Mujhe ek naya folder bana ke do aur iska naam College Projects rakh do.", "category": "Hinglish Folder Creation", "check": lambda r: "college projects" in r.lower() or "folder" in r.lower()},
        {"cmd": "Notepad kholo", "category": "Hinglish App Launch", "check": lambda r: "notepad" in r.lower()},
        {"cmd": "Calculator open kar do", "category": "Hinglish App Launch", "check": lambda r: "calculator" in r.lower()},
        {"cmd": "Isko band karo", "category": "Hinglish Contextual Pronoun Close", "check": lambda r: "calculator" in r.lower() or "band" in r.lower()},
        {"cmd": "Jo abhi bola tha woh repeat karo.", "category": "Hinglish Context Memory Repeat", "check": lambda r: "maine kaha tha" in r.lower() or "calculator" in r.lower()},
        {"cmd": "Thank you Jarvis, bohot badhiya kaam kiya.", "category": "Hinglish Gratitude", "check": lambda r: any(k in r.lower() for k in ["welcome", "coffee", "credit", "tareef", "anytime"])},
        {"cmd": "Hey Jarvis, suno", "category": "Hinglish Greeting / Wake", "check": lambda r: any(k in r.lower() for k in ["boss", "jarvis", "bolo", "online"])},
        {"cmd": "Google pe dhoondo best python libraries", "category": "Hinglish Web Search", "check": lambda r: "google" in r.lower() or "search" in r.lower()},
        {"cmd": "Laptop lock kar do", "category": "Hinglish System Lock", "check": lambda r: "lock" in r.lower()},

        # --- Pure Hindi Commands ---
        {"cmd": "आज का समय क्या है?", "category": "Hindi Date & Time", "check": lambda r: "तारीख" in r or "समय" in r},
        {"cmd": "नमस्ते जार्विस, कैसी हो?", "category": "Hindi Greeting", "check": lambda r: "नमस्ते" in r or "जार्विस" in r},

        # --- English Commands ---
        {"cmd": "Open Google Chrome please", "category": "English App Launch", "check": lambda r: "chrome" in r.lower()},
        {"cmd": "What time is it right now?", "category": "English Date & Time", "check": lambda r: any(k in r.lower() for k in ["am", "pm", "time", "currently", "2026"])},
        {"cmd": "Decrease screen brightness", "category": "English Brightness", "check": lambda r: "brightness" in r.lower()},
        {"cmd": "Mute the system volume", "category": "English Volume Mute", "check": lambda r: "mute" in r.lower()},
        {"cmd": "Search for Python documentation on Google", "category": "English Search", "check": lambda r: "google" in r.lower() or "search" in r.lower()},
        {"cmd": "Tell me a programmer joke", "category": "English Humor", "check": lambda r: any(k in r.lower() for k in ["binary", "bug", "bugs", "light", "people", "dark mode"])},
        {"cmd": "Help me debug a SyntaxError in Python", "category": "English Code Diagnostics", "check": lambda r: any(k in r.lower() for k in ["error", "bug", "colon", "syntax"])},
        {"cmd": "Create a new folder named WorkReports", "category": "English Folder Creation", "check": lambda r: "workreports" in r.lower() or "folder" in r.lower()},
        {"cmd": "Close notepad", "category": "English App Termination", "check": lambda r: "notepad" in r.lower()},
        {"cmd": "Thanks a lot for your help", "category": "English Gratitude", "check": lambda r: any(k in r.lower() for k in ["welcome", "coffee", "anytime", "ready"])}
    ]

    passed = 0
    failed = 0

    for idx, test in enumerate(test_cases, 1):
        cmd = test["cmd"]
        cat = test["category"]
        print(f"\n[{idx:02d}/32] Category: {cat}")
        print(f"       Input   : \"{cmd}\"")
        try:
            response = brain.process_command(cmd)
            print(f"       Response: \"{response.splitlines()[0]}\"")
            if test["check"](response):
                print(f"       Status  : PASS [OK]")
                passed += 1
            else:
                print(f"       Status  : FAIL (Output check condition not met)")
                failed += 1
        except Exception as e:
            print(f"       Status  : ERROR ({e})")
            failed += 1

    print("\n" + "=" * 65)
    print(f"TEST RUN COMPLETE: {passed} PASSED, {failed} FAILED (Total: {len(test_cases)})")
    print(f"Pass Rate: {(passed / len(test_cases)) * 100:.1f}%")
    print("=" * 65)
    return passed == len(test_cases)

if __name__ == "__main__":
    success = run_jarvis_test_suite()
    sys.exit(0 if success else 1)
