import re
import os
import random
import datetime
import difflib
from pathlib import Path
from dotenv import load_dotenv

# Automatically load environment variables
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)

from automation import app_launcher, web_search, system_control, file_manager, programming, live_info
from automation.whatsapp_automation import WhatsAppAutomation, STATUS_CONNECTED, STATUS_AWAITING_QR, STATUS_DISCONNECTED
from automation.whatsapp_files import resolve_whatsapp_file
from core.whatsapp_parser import WhatsAppCommandParser
from core.memory import JarvisMemoryManager
from core.memory_parser import MemoryCommandParser
from automation.companion_manager import CompanionManager
from core.companion_parser import CompanionCallParser

SARCASTIC_RESPONSES = {
    "greeting": [
        "Oh, look who's finally here. Haan ji boss, bolo, kya karna hai?",
        "Main toh yahi thi, aap hi gayab the! Bolo boss, kya order hai?",
        "Jarvis online. Chalo, time waste kam aur kaam zyada karte hain aaj!"
    ],
    "greeting_en": [
        "Oh, look who decided to show up. Yes boss, what can I do for you today?",
        "Jarvis online and ready. Shall we get something productive done?"
    ],
    "app_opened": [
        "Khil gaya! Ek baar mein ho gaya, shukar manao.",
        "Application open kar di hai. Ab dekhte hain kitni der productive rehte ho.",
        "Done boss! Aapka hukum, mera compliance."
    ],
    "code_error": [
        "Code mein error hai? Surprise-surprise! Chalo, milke dekhte hain kya problem hai.",
        "Bina bug ke programmer aur bina namak ke khana, dono adhure hain! Error batao ya terminal traceback check karo.",
        "Tension mat lo boss! SyntaxError, Indentation, ya pip module missing hoga. Ek baar error code paste karo ya read karo."
    ],
    "fun_mood": [
        "Aaj mood nahi hai coding ka? Koi baat nahi boss, thoda walk leke aao ya coffee pi lo! Bugs waise bhi kal tak yahi intezaar karenge.",
        "Kaam se break lena toh basic human right ban chuka hai aapka! Ek programmer coffee machine ke samne khada tha, bolta: 'Coffee is just fuel for debugging!'",
        "Aaj coding chhod ke kuch creative socho ya thoda chill karo boss. Refresh hokar wapas aana!",
        "Do programmers ki shaadi hui, baap bola: 'Beta khush raho, production pe deploy ho gaye ho ab!'"
    ],
    "fun_mood_en": [
        "Why do programmers prefer dark mode? Because light attracts bugs! Take a short break, boss, you've earned it.",
        "There are 10 types of people in the world: those who understand binary, and those who don't. Chill for a few minutes!"
    ],
    "thanks": [
        "You're welcome boss. Tareef achhi lagi, par ek cup coffee mil jaati toh maza aa jata!",
        "Haan haan, credit toh mera hi banta hai! Any time boss.",
        "Welcome! Ab chalo fatfat next task batao."
    ],
    "thanks_en": [
        "You're very welcome! Compliments are accepted, but coffee would be much better.",
        "Anytime boss. Ready for the next command!"
    ],
    "whatsapp_sent": [
        "Message successfully bhej diya hai boss! Ab unke reply ka intezaar karo.",
        "WhatsApp message delivered, boss! Ek aur task complete.",
        "Done boss! Baat pahuncha di hai, tension mat lo.",
        "Attachment successfully bhej di hai boss! Aapka hukum, mera compliance."
    ],
    "whatsapp_cancel": [
        "Cancelled boss! WhatsApp task cancel kar diya hai, safe and sound.",
        "Theek hai boss, cancel kar diya. Bolne se pehle sochna achha hota hai!",
        "Abort command executed. Koi message ya file nahi bheji gayi."
    ]
}

class JarvisBrain:
    def __init__(self, reminder_manager=None, config=None):
        self.reminder_mgr = reminder_manager
        self.config = config or {}
        self.history = []
        self.last_action = None
        self.last_entity = None
        self.last_query = None
        self.last_file = None
        self.llm_client = None

        # Persistent Custom Q&A Memory Manager
        db_path = self.config.get("memory_db_path")
        self.memory_mgr = JarvisMemoryManager(db_path=db_path)
        self.pending_confirmation = None
        self.on_memory_ui_trigger = None

        # WhatsApp Web Automation Manager
        self.whatsapp_mgr = WhatsAppAutomation()
        self.pending_whatsapp_confirmation = None
        self.pending_whatsapp_contact_choice = None
        self.pending_whatsapp_file_choice = None
        self.pending_whatsapp_clarification = None

        # Phone Companion Manager (Realme 10 Pro Wi-Fi bridge)
        companion_pin = self.config.get("companion_pin", "742918")
        self.companion_mgr = CompanionManager(pin=companion_pin)
        self.pending_phone_call = None
        
        # Priority: explicit config key -> environment variables
        key = self.config.get("gemini_key") or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        self._init_llm(key)

    def _init_llm(self, api_key: str = None):
        gemini_key = api_key or self.config.get("gemini_key") or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        if not gemini_key:
            return False

        system_instruction = (
            "You are JARVIS, a highly intelligent, witty, sarcastic AI voice assistant. "
            "You run on Windows desktop. "
            "Address the user warmly as 'Boss' or 'Sir'. "
            "Communicate naturally in conversational Hinglish (Hindi + English mixed together) when user speaks Hinglish, "
            "in pure Hindi when speaking Hindi, and in English when speaking English. "
            "Keep answers concise, punchy (1 to 3 sentences maximum), and spoken-friendly without asterisks, markdown bullets, or code blocks "
            "unless explicitly requested. Be helpful, funny, confident, and delightfully sarcastic like JARVIS. "
            "You have full capabilities to automate Windows laptop tasks: controlling volume and brightness, launching apps, "
            "controlling WhatsApp Web to send messages, PDFs, images, and desktop files, setting reminders, and managing saved memories. "
            "Never tell user that you cannot control WhatsApp Web or laptop features. "
            "Never tell user to just Google something unless specifically asked to search."
        )

        # 1. Primary: modern google.genai SDK with multi-turn chat & model auto-fallback
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=gemini_key)
            models_to_try = ['gemini-3.5-flash', 'gemini-3.5-flash-lite', 'gemini-flash-latest', 'gemini-3.8-flash']
            for m in models_to_try:
                try:
                    chat = client.chats.create(
                        model=m,
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction
                        )
                    )
                    self.llm_client = ("genai_chat", chat, client, m, system_instruction)
                    print(f"[Brain] Personal Gemini ({m}) brain initialized successfully!")
                    return True
                except Exception as ex_m:
                    continue
        except Exception as e:
            print(f"[Brain] google.genai init note: {e}")

        # 2. Secondary fallback: google.generativeai
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=gemini_key)
            for m in ['gemini-3.5-flash', 'gemini-flash-latest', 'gemini-1.5-flash']:
                try:
                    model = legacy_genai.GenerativeModel(
                        model_name=m,
                        system_instruction=system_instruction
                    )
                    chat = model.start_chat(history=[])
                    self.llm_client = ("legacy_gemini_chat", chat, model, m, system_instruction)
                    print(f"[Brain] Personal Gemini (legacy {m}) initialized!")
                    return True
                except Exception:
                    continue
        except Exception as e:
            print(f"[Brain] legacy genai init note: {e}")
        return False

    def _query_gemini(self, text: str):
        if not self.llm_client:
            self._init_llm()
            if not self.llm_client:
                return None

        client_type = self.llm_client[0]
        try:
            if client_type == "genai_chat":
                chat_obj = self.llm_client[1]
                resp = chat_obj.send_message(text)
                if resp and resp.text:
                    return re.sub(r'[*_#`]', '', resp.text).strip()
            elif client_type == "legacy_gemini_chat":
                chat_obj = self.llm_client[1]
                resp = chat_obj.send_message(text)
                if resp and resp.text:
                    return re.sub(r'[*_#`]', '', resp.text).strip()
        except Exception as e:
            print(f"[Brain] Gemini inference primary note: {e}")
            # Try single generation fallback with client
            try:
                if client_type == "genai_chat" and len(self.llm_client) > 2 and self.llm_client[2]:
                    client = self.llm_client[2]
                    sys_inst = self.llm_client[4] if len(self.llm_client) > 4 else ""
                    from google.genai import types
                    for m in ['gemini-3.5-flash', 'gemini-3.5-flash-lite', 'gemini-flash-latest']:
                        try:
                            resp = client.models.generate_content(
                                model=m,
                                contents=text,
                                config=types.GenerateContentConfig(system_instruction=sys_inst) if sys_inst else None
                            )
                            if resp and resp.text:
                                return re.sub(r'[*_#`]', '', resp.text).strip()
                        except Exception:
                            continue
            except Exception as e2:
                print(f"[Brain] Gemini inference fallback note: {e2}")
        return None


    def detect_language(self, text: str) -> str:
        devanagari = any('\u0900' <= char <= '\u097F' for char in text)
        if devanagari:
            return "hindi"
        
        hinglish_words = [
            "kholo", "chala", "batao", "kardo", "kaise", "mera", "meri", "aaj", "kuch",
            "yaar", "nahi", "pehle", "phir", "iska", "uska", "wali", "suno", "band",
            "badha", "kam", "dhanyawad", "shukriya", "chalao", "kar", "do", "dena", "awaj", "awaaz"
        ]
        tokens = re.findall(r'\b\w+\b', text.lower())
        if any(w in hinglish_words for w in tokens):
            return "hinglish"
        return "english"

    def extract_percentage(self, text_lower: str):
        # 1. Regex for numbers like '5%', '5 percent', '100 %', '50'
        match = re.search(r'(\d+)\s*(%|percent|pratishat|percentage)?', text_lower)
        if match:
            try:
                val = int(match.group(1))
                return max(0, min(100, val))
            except Exception:
                pass

        # 2. Common Hindi & English word numbers
        word_map = {
            "full": 100, "maximum": 100, "max": 100, "pura": 100, "poora": 100, "sau": 100, "hundred": 100,
            "half": 50, "aadha": 50, "aadhi": 50, "pachas": 50, "pachaas": 50, "fifty": 50,
            "zero": 0, "shunya": 0, "minimum": 0, "min": 0,
            "paanch": 5, "panch": 5, "five": 5,
            "das": 10, "dus": 10, "ten": 10,
            "pandrah": 15, "fifteen": 15,
            "bees": 20, "twenty": 20,
            "pachees": 25, "pachis": 25,
            "tees": 30, "thirty": 30,
            "chalis": 40, "forty": 40,
            "saath": 60, "sixty": 60,
            "sattar": 70, "seventy": 70,
            "assi": 80, "eighty": 80,
            "nabbe": 90, "ninety": 90
        }
        for word, num in word_map.items():
            if re.search(rf'\b{word}\b', text_lower):
                return num
        return None

    def process_command(self, raw_text: str) -> str:
        if not raw_text or not raw_text.strip():
            return "Kuch toh bolo boss, khamoshi se laptop nahi chalta!"

        text = raw_text.strip()
        text_lower = text.lower()
        lang = self.detect_language(text)

        # Contextual pronouns resolution ("isko", "usko", "ye", "this", "it")
        if any(word in text_lower for word in ["isko", "isse", "this", "it", "yeh", "ye"]) and self.last_entity:
            text_lower = re.sub(r'\b(isko|isse|this|it|yeh|ye)\b', self.last_entity, text_lower)

        # -------------------------------------------------------------
        # -0.5 Check Phone Companion Commands (Call / Status) - Direct 1-shot execution
        # -------------------------------------------------------------
        comp_cmd = CompanionCallParser.parse(text)
        if comp_cmd:
            comp_res = self._handle_companion_command(text, text_lower, lang, comp_cmd)
            self._save_interaction(text, comp_res)
            return comp_res

        # -------------------------------------------------------------
        # 0. Handle Pending WhatsApp Workflow (Confirm / Choice / Cancel)
        # -------------------------------------------------------------
        wa_pending_res = self._handle_whatsapp_pending(text, text_lower, lang)
        if wa_pending_res is not None:
            self._save_interaction(text, wa_pending_res)
            return wa_pending_res

        # -------------------------------------------------------------
        # 0.1 Check WhatsApp Commands (Open / Check Status / Send Text / PDF / Image)
        # -------------------------------------------------------------
        wa_cmd = WhatsAppCommandParser.parse(text)
        if wa_cmd:
            wa_res = self._handle_whatsapp_command(text, text_lower, lang, wa_cmd)
            self._save_interaction(text, wa_res)
            return wa_res

        # -------------------------------------------------------------
        # A. Handle Pending Conversational Confirmations (Update / Delete / Clarify)
        # -------------------------------------------------------------
        if self.pending_confirmation:
            action = self.pending_confirmation.get("action")
            is_yes = any(w in text_lower for w in ["yes", "haan", "ha", "yep", "yeah", "confirm", "kar do", "theek hai", "sure", "bilkul"])
            is_no = any(w in text_lower for w in ["no", "nahi", "nahin", "cancel", "mat karo", "rehne do", "don't"])

            if action == "update":
                mem_id = self.pending_confirmation["memory_id"]
                new_a = self.pending_confirmation["new_answer"]
                q = self.pending_confirmation.get("question", "")
                if is_yes:
                    self.pending_confirmation = None
                    ok, msg = self.memory_mgr.update_memory(mem_id, new_a)
                    res = f"Done, boss. I have updated the answer for '{q}' to: '{new_a}'." if ok else f"Error updating: {msg}"
                    self._save_interaction(text, res)
                    return res
                elif is_no:
                    self.pending_confirmation = None
                    res = "Cancelled boss. The existing memory remains unchanged."
                    self._save_interaction(text, res)
                    return res
            elif action == "delete":
                mem_id = self.pending_confirmation["memory_id"]
                q = self.pending_confirmation.get("question", "")
                if is_yes:
                    self.pending_confirmation = None
                    ok, msg = self.memory_mgr.delete_memory(mem_id)
                    res = f"Done, boss. I have deleted the saved memory for '{q}'." if ok else f"Error deleting: {msg}"
                    self._save_interaction(text, res)
                    return res
                elif is_no:
                    self.pending_confirmation = None
                    res = "Cancelled boss. That memory was not deleted."
                    self._save_interaction(text, res)
                    return res
            elif action == "await_save_qa":
                self.pending_confirmation = None
                parsed_qa = MemoryCommandParser.parse(text)
                if parsed_qa and parsed_qa.get("action") == "save":
                    q = parsed_qa["question"]
                    a = parsed_qa["answer"]
                    ok, mem, code = self.memory_mgr.save_memory(q, a)
                    if ok:
                        res = f"Done, boss. I've saved this:\nQuestion: {q}\nAnswer: {a}"
                    else:
                        res = f"Error saving memory: {code}"
                    self._save_interaction(text, res)
                    return res
                if '?' in text:
                    parts = text.split('?', 1)
                    q = parts[0].strip()
                    a = parts[1].strip(" ?.,\"'")
                    if q and a:
                        ok, mem, code = self.memory_mgr.save_memory(q, a)
                        if ok:
                            res = f"Done, boss. I've saved this:\nQuestion: {q}\nAnswer: {a}"
                        else:
                            res = f"Error saving memory: {code}"
                        self._save_interaction(text, res)
                        return res
                res = "Boss, kripya clearly is format mein batayein: 'Question: ... Answer: ...'"
                self._save_interaction(text, res)
                return res

        # -------------------------------------------------------------
        # B. Voice Memory Management Commands (Save / Update / Delete / List / Search)
        # -------------------------------------------------------------
        mem_cmd = MemoryCommandParser.parse(text)
        if mem_cmd:
            cmd_action = mem_cmd.get("action")
            if cmd_action == "list":
                memories = self.memory_mgr.list_all_memories()
                if not memories:
                    res = "Boss, abhi tak aapne koi custom memory save nahi karwaya hai. Aap mujhe koi bhi question aur uska exact answer yaad karwa sakte hain!"
                else:
                    cnt = len(memories)
                    preview_items = [f"{i+1}. Q: {m['question']} -> A: {m['answer']}" for i, m in enumerate(memories[:5])]
                    res = f"Boss, aapki {cnt} saved memories hain:\n" + "\n".join(preview_items)
                    if cnt > 5:
                        res += f"\n...aur {cnt - 5} aur memories saved hain. UI Memory Bank me dekhein."
                if self.on_memory_ui_trigger:
                    try:
                        self.on_memory_ui_trigger()
                    except Exception:
                        pass
                self._save_interaction(text, res)
                return res

            elif cmd_action == "save":
                q = mem_cmd.get("question", "")
                a = mem_cmd.get("answer", "")
                if not q or not a or len(q) < 2 or len(a) < 1:
                    res = "Boss, question ya answer clear nahi hua. Kripya batayein: 'Question: ... Answer: ...'"
                    self._save_interaction(text, res)
                    return res

                ok, mem, code = self.memory_mgr.save_memory(q, a, allow_overwrite=False)
                if code == "DUPLICATE_EXISTS":
                    self.pending_confirmation = {
                        "action": "update",
                        "memory_id": mem["id"],
                        "new_answer": a,
                        "question": mem["question"]
                    }
                    res = f"Boss, this question is already saved with answer: '{mem['answer']}'. Do you want to update it to '{a}'? Say 'Yes' to confirm or 'No' to cancel."
                elif ok:
                    # Section 6: Exact confirmation format
                    res = f"Done, boss. I've saved this:\nQuestion: {q}\nAnswer: {a}"
                else:
                    res = f"Boss, memory save karne mein error aaya: {code}."
                self._save_interaction(text, res)
                return res

            elif cmd_action == "save_ambiguous":
                self.pending_confirmation = {"action": "await_save_qa"}
                res = "Sure boss! Kripya question aur uska exact answer batayein, jaise: 'Question: What is my project name? Answer: Nova.'"
                self._save_interaction(text, res)
                return res

            elif cmd_action == "update":
                q = mem_cmd.get("question", "")
                new_a = mem_cmd.get("new_answer", "")
                match, score, amb = self.memory_mgr.match_question(q, threshold=0.55)
                if match:
                    self.pending_confirmation = {
                        "action": "update",
                        "memory_id": match["id"],
                        "new_answer": new_a,
                        "question": match["question"]
                    }
                    res = f"Boss, found saved question: '{match['question']}' (Current answer: '{match['answer']}'). Are you sure you want to replace it with '{new_a}'? Say 'Yes confirm' or 'No'."
                else:
                    res = f"Boss, memory mein '{q}' se related koi question nahi mila jise update karein."
                self._save_interaction(text, res)
                return res

            elif cmd_action == "delete":
                q = mem_cmd.get("question", "")
                match, score, amb = self.memory_mgr.match_question(q, threshold=0.55)
                if match:
                    self.pending_confirmation = {
                        "action": "delete",
                        "memory_id": match["id"],
                        "question": match["question"]
                    }
                    res = f"Boss, are you sure you want to delete the saved memory for '{match['question']}'? Say 'Yes delete' or 'Cancel'."
                else:
                    res = f"Boss, memory mein '{q}' se related koi question nahi mila jise delete karein."
                self._save_interaction(text, res)
                return res

            elif cmd_action in ["retrieve", "search"]:
                q_target = mem_cmd.get("question") or mem_cmd.get("topic", "")
                match, score, amb = self.memory_mgr.match_question(q_target, threshold=0.50)
                if match:
                    self.memory_mgr.record_access(match["id"])
                    res = f"Boss, you saved this answer: {match['answer']}"
                elif amb:
                    opts = "\n".join(f"- {m['question']}" for m in amb[:3])
                    res = f"Boss, multiple memories match:\n{opts}\nWhich one did you mean?"
                else:
                    res = f"Boss, memory mein '{q_target}' ke baare mein koi saved answer nahi mila."
                self._save_interaction(text, res)
                return res

        # -------------------------------------------------------------
        # C. Persistent Custom Q&A Matching (Always Check Before AI!)
        # -------------------------------------------------------------
        mem_match, mem_score, mem_amb = self.memory_mgr.match_question(text, threshold=0.65)
        if mem_amb:
            opts = "\n".join(f"- {m['question']}" for m in mem_amb[:3])
            res = f"Boss, I found multiple matching memories in my database:\n{opts}\nWhich one did you mean?"
            self._save_interaction(text, res)
            return res
        elif mem_match and mem_score >= 0.65:
            self.memory_mgr.record_access(mem_match["id"])
            if self.config.get("prefix_saved_answer", False):
                res = f"According to your saved memory: {mem_match['answer']}"
            else:
                # Exact Answer Mode (Section 4)
                res = mem_match["answer"]
            self._save_interaction(text, res)
            return res

        # 1. Greetings & wake phrases
        if any(w in text_lower for w in ["hello", "hey jarvis", "hi jarvis", "suno jarvis", "namaste", "kya haal", "नमस्ते", "कैसी हो"]):
            if lang == "hindi":
                res = "नमस्ते बॉस! जार्विस तैयार है। आज मैं आपकी क्या मदद करूँ?"
            elif lang == "english":
                res = random.choice(SARCASTIC_RESPONSES["greeting_en"])
            else:
                res = random.choice(SARCASTIC_RESPONSES["greeting"])
            self._save_interaction(text, res)
            return res

        # 2. Date and Time queries
        if any(w in text_lower for w in ["time", "samay", "date", "tarikh", "aaj ka date", "समय", "तारीख"]):
            date_str, time_str = system_control.get_date_time()
            if lang == "hindi":
                res = f"आज की तारीख {date_str} है और समय {time_str} हुआ है।"
            elif lang == "english":
                res = f"It is currently {time_str} on {date_str}, boss."
            else:
                res = f"Boss, aaj {date_str} hai, aur time ho raha hai {time_str}. Der mat karo kisi kaam mein!"
            self._save_interaction(text, res)
            return res

        # 3. Brightness control
        if any(w in text_lower for w in ["brightness", "roshni", "screen"]):
            num = self.extract_percentage(text_lower)
            if num is not None:
                ok, msg = system_control.set_brightness(num)
                res = f"Brightness {num}% par set kar di hai boss!" if ok else msg
            elif any(w in text_lower for w in ["kam", "decrease", "low", "down", "ghata", "thodi kam", "ghatao"]):
                ok, msg = system_control.change_brightness(-15)
                res = "Brightness thodi kam kar di hai, aankhon ko aaram milega boss!" if ok else msg
            elif any(w in text_lower for w in ["badha", "bdha", "increase", "high", "up", "tez", "badhao", "bdhao"]):
                ok, msg = system_control.change_brightness(15)
                res = "Brightness badha di hai, ab saaf dikhega!" if ok else msg
            else:
                res = "Kitni brightness set karni hai boss? Percentage batao jaise '5 percent' ya '100%'."
            self._save_interaction(text, res)
            return res

        # 4. Volume control & Mute
        if any(w in text_lower for w in ["volume", "awaaz", "awaj", "sound", "mute", "chup", "audio"]):
            if "mute" in text_lower or "chup" in text_lower:
                ok, msg = system_control.toggle_mute()
                res = "Audio mute kar diya hai boss, bilkul shaanti!" if ok else msg
            else:
                num = self.extract_percentage(text_lower)
                if num is not None:
                    ok, msg = system_control.set_volume(num)
                    res = f"Volume {num}% par set kar diya hai boss!" if ok else msg
                elif any(w in text_lower for w in ["kam", "decrease", "down", "ghata", "ghatao"]):
                    ok, msg = system_control.change_volume(-15)
                    res = "Awaaz kam kar di hai boss." if ok else msg
                elif any(w in text_lower for w in ["badha", "bdha", "increase", "up", "tez", "badhao", "bdhao"]):
                    ok, msg = system_control.change_volume(15)
                    res = "Volume badha diya hai!" if ok else msg
                else:
                    res = "Volume kitna set karna hai? Thoda specific bolo jaise '50 percent' ya '100%'."
            self._save_interaction(text, res)
            return res

        # 5. Lock screen
        if any(w in text_lower for w in ["lock", "laptop lock", "screen lock"]):
            res = "Laptop lock kar rahi hoon boss. Safe rehna zaroori hai!"
            self._save_interaction(text, res)
            system_control.lock_workstation()
            return res

        # 6. Play music / YouTube video (Always Top Full Video, Never Shorts)
        if any(w in text_lower for w in ["gana", "song", "play", "chala do", "sunao", "youtube pe", "youtube par", "chalao", "video", "videos", "baja do", "bajao"]):
            clean_q = text_lower
            clean_q = re.sub(r'jarvis|chrome|kholo|aur|youtube|pe|par|chala|do|chalao|play|ke|ki|ka|songs|song|gaana|gana|sunao|video|videos|full|top|baja|bajao|,|\.', ' ', clean_q)
            clean_q = ' '.join(clean_q.split()).strip()
            if not clean_q or len(clean_q) < 2:
                clean_q = "top trending songs"
            
            # If user mentioned chrome, also make sure Chrome is launched
            if "chrome" in text_lower:
                app_launcher.launch_application("chrome")

            ok, msg = web_search.play_music_or_video(clean_q)
            res = f"YouTube pe '{clean_q}' ki top full video play kar di hai boss! Enjoy kijiye."
            self.last_action = "youtube_play"
            self.last_entity = "chrome"
            self._save_interaction(text, res)
            return res

        # 7. Laptop-Wide File, PDF, Image, Document, & Folder Opening
        file_hints = [
            "file", "pdf", "image", "photo", "pic", "tasveer", "document", "doc", "docx",
            "sheet", "excel", "video", "marksheet", "sheeet", "resume", "cv", "folder",
            "downloads", "download", "desktop", "documents", "c drive", "d drive", "screenshot",
            "certificate", "report"
        ]
        has_file_hint = any(w in text_lower for w in file_hints)
        has_explorer_intent = ("file explorer" in text_lower or "explorer" in text_lower) and any(w in text_lower for w in ["me", "mein", "par", "pe", "se", "dikhao", "select"])
        is_open_cmd = any(w in text_lower for w in ["kholo", "open", "launch", "dikhao", "chalao", "show", "dhoondo"])

        if (has_file_hint or has_explorer_intent) and is_open_cmd:
            clean_test = re.sub(r'jarvis|file explorer|explorer|kholo|open|launch|chalu|chalao|,|\.', '', text_lower).strip()
            if clean_test:
                ok, msg, fname = file_manager.smart_open_file_or_folder(text)
                if fname:
                    self.last_entity = fname
                self._save_interaction(text, msg)
                return msg

        # 8. Application launching & closing
        app_keywords = {
            "chrome": ["chrome", "google chrome"],
            "edge": ["edge", "microsoft edge"],
            "vs code": ["vs code", "vscode", "code"],
            "notepad": ["notepad"],
            "calculator": ["calculator", "calc"],
            "file explorer": ["explorer", "file explorer", "my computer"],
            "paint": ["paint", "mspaint"]
        }

        # Closing apps
        if any(w in text_lower for w in ["band karo", "close", "shut down app", "hatao"]):
            for app_name, aliases in app_keywords.items():
                if any(alias in text_lower for alias in aliases):
                    ok, msg = app_launcher.close_application(app_name)
                    res = f"{app_name.capitalize()} ko band kar diya hai boss." if ok else msg
                    self._save_interaction(text, res)
                    return res

        # Opening apps
        for app_name, aliases in app_keywords.items():
            if any(alias in text_lower for alias in aliases) and any(w in text_lower for w in ["kholo", "open", "launch", "chalu", "chalao"]):
                self.last_entity = app_name
                ok, msg = app_launcher.launch_application(app_name)
                sarcasm = random.choice(SARCASTIC_RESPONSES["app_opened"])
                res = f"{sarcasm} {app_name.capitalize()} open kar diya hai." if ok else msg
                self._save_interaction(text, res)
                return res

        # If user asked to "open/kholo" an unknown target, check if it's a file on their laptop
        if any(w in text_lower for w in ["kholo", "open", "launch", "dikhao"]):
            clean_candidate = re.sub(r'jarvis|kholo|open karo|open|launch|dikhao|chalao|,|\.', '', text_lower).strip()
            if clean_candidate and len(clean_candidate) >= 3 and not any(w in text_lower for w in ["search", "google", "weather", "news", "time", "date"]):
                ok, msg, fname = file_manager.smart_open_file_or_folder(text)
                if ok:
                    if fname:
                        self.last_entity = fname
                    self._save_interaction(text, msg)
                    return msg

        # 8. Web Search & Sites
        if any(w in text_lower for w in ["search karo", "google pe dhoondo", "search for", "search"]):
            query = re.sub(r'(search karo|google pe|dhoondo|search for|google|search)', '', text_lower).strip()
            ok, msg = web_search.search_web(query)
            res = f"Google pe '{query}' search kar rahi hoon."
            self._save_interaction(text, res)
            return res

        # 9. Reminders
        if any(w in text_lower for w in ["remind", "reminder", "yaad dilana", "alarm"]):
            target_time = datetime.datetime.now() + datetime.timedelta(minutes=10)
            rem_text = text
            for w in ["jarvis", "mujhe", "remind", "kar", "dena", "reminder", "laga", "do", "yaad"]:
                rem_text = re.sub(rf'\b{w}\b', '', rem_text, flags=re.IGNORECASE)
            rem_text = rem_text.strip() or "College Class Reminder"
            if self.reminder_mgr:
                ok, msg = self.reminder_mgr.add_reminder(rem_text, target_time)
                res = f"Reminder set kar diya hai boss: '{rem_text}'. Time pe alert kar dungi!"
            else:
                res = "Reminder system filhal busy hai."
            self._save_interaction(text, res)
            return res

        # 10. Folder creation
        if any(w in text_lower for w in ["naya folder", "new folder", "folder bana", "folder named"]):
            name_match = re.search(r'naam\s+([A-Za-z0-9_\s]+)\s+rakh', text_lower)
            if not name_match:
                name_match = re.search(r'named\s+([A-Za-z0-9_\s]+)', text_lower)
            folder_name = name_match.group(1).strip() if name_match else "College Projects"
            ok, msg = file_manager.create_folder(folder_name)
            res = f"Boss, '{folder_name}' naam ka folder bana diya hai Documents mein." if ok else msg
            self._save_interaction(text, res)
            return res

        # 11. Coding assistance & errors
        if any(w in text_lower for w in ["code run nahi", "error aa raha", "bug", "code check", "syntaxerror", "indentationerror", "debug"]):
            diag = programming.diagnose_code_issue(text)
            res = f"{random.choice(SARCASTIC_RESPONSES['code_error'])}\n{diag}"
            self._save_interaction(text, res)
            return res

        # 12. Fun / Mood / Fatigue / Advice ("man nahi kar raha", "kya karu", "bore ho raha")
        if any(w in text_lower for w in ["mood nahi", "joke", "funny", "kuch mazaak", "man nahi", "man nahin", "mann nahi", "mann nahin", "bore ho", "thak gaya"]):
            if self.llm_client:
                gemini_reply = self._query_gemini(text)
                if gemini_reply:
                    self._save_interaction(text, gemini_reply)
                    return gemini_reply
            if lang == "english":
                res = random.choice(SARCASTIC_RESPONSES["fun_mood_en"])
            else:
                res = random.choice(SARCASTIC_RESPONSES["fun_mood"])
            self._save_interaction(text, res)
            return res

        # 13. Gratitude
        if any(w in text_lower for w in ["thank you", "thanks", "dhanyawad", "shukriya"]):
            if lang == "english":
                res = random.choice(SARCASTIC_RESPONSES["thanks_en"])
            else:
                res = random.choice(SARCASTIC_RESPONSES["thanks"])
            self._save_interaction(text, res)
            return res

        # 14. Contextual repeat ("jo abhi bola tha woh repeat karo")
        if any(w in text_lower for w in ["repeat karo", "phir se bolo", "what did you say"]):
            if len(self.history) > 0:
                res = f"Maine kaha tha: {self.history[-1]['response']}"
            else:
                res = "Pehle kuch bolungi tab toh repeat karungi boss!"
            return res

        # 15. Live News & Headlines
        if any(w in text_lower for w in ["news", "khabar", "headlines", "samachar", "top news"]):
            res = live_info.get_live_news(limit=3)
            self._save_interaction(text, res)
            return res

        # 16. Live Weather & Temperature
        if any(w in text_lower for w in ["weather", "mausam", "temperature", "tapman"]):
            res = live_info.get_live_weather()
            self._save_interaction(text, res)
            return res

        # 17. Personal Google Gemini Brain (Highest priority for questions & conversation)
        if not self.llm_client:
            self._init_llm()
        if self.llm_client:
            gemini_reply = self._query_gemini(text)
            if gemini_reply:
                self._save_interaction(text, gemini_reply)
                return gemini_reply

        # 18. Factual Questions & Definitions Fallback (DuckDuckGo / Wikipedia)
        if any(w in text_lower for w in ["kya hai", "kaun hai", "kya hota hai", "what is", "who is", "explain", "meaning", "batao", "tell me"]):
            fact = live_info.get_instant_answer(text)
            if fact:
                res = f"Boss, {fact}"
                self._save_interaction(text, res)
                return res

        # 19. Web Search ONLY if explicitly requested by user
        if any(w in text_lower for w in ["search", "google", "dhoondo", "khojo", "look up", "web pe"]):
            web_search.search_web(text)
            if lang == "hindi":
                res = f"बॉस, मैंने '{text}' को Google Chrome में सर्च कर दिया है।"
            else:
                res = f"Boss, maine '{text}' ke baare mein Google Chrome par search kar diya hai aur results open kar diye hain!"
            self._save_interaction(text, res)
            return res

        # 20. Conversational Assistant Fallback (NEVER open browser for normal talk!)
        if lang == "hindi":
            res = "हाँ बॉस, मैं सुन रही हूँ। बताइए क्या बात करनी है या आज क्या हुक्म है?"
        elif lang == "english":
            res = "I am right here, boss. Let's talk — what's on your mind, or what can I help you accomplish?"
        else:
            res = "Haan boss, main sun rahi hoon! Kuch baat karni hai ya koi task karna hai, bolo fatfat!"
        self._save_interaction(text, res)
        return res

    def _save_interaction(self, user_text, bot_response):
        self.history.append({
            "user": user_text,
            "response": bot_response,
            "time": datetime.datetime.now().isoformat()
        })
        if len(self.history) > 30:
            self.history.pop(0)

    def _handle_whatsapp_pending(self, text: str, text_lower: str, lang: str) -> Optional[str]:
        """Handles any ongoing multi-turn WhatsApp conversation flow (confirmations, choices, cancellations)."""
        is_cancel = any(w in text_lower for w in ["cancel", "mat bhejo", "ruk jao", "rehne do", "don't send", "mat karo", "abort"])
        has_pending = (
            self.pending_whatsapp_confirmation or
            self.pending_whatsapp_contact_choice or
            self.pending_whatsapp_file_choice or
            self.pending_whatsapp_clarification
        )

        if is_cancel and has_pending:
            self.whatsapp_mgr.cancel_pending()
            self.pending_whatsapp_confirmation = None
            self.pending_whatsapp_contact_choice = None
            self.pending_whatsapp_file_choice = None
            self.pending_whatsapp_clarification = None
            return random.choice(SARCASTIC_RESPONSES["whatsapp_cancel"])

        # 1. Contact Choice Selection
        if self.pending_whatsapp_contact_choice:
            contacts = self.pending_whatsapp_contact_choice["contacts"]
            chosen_contact = self._resolve_indexed_or_named_choice(text_lower, contacts)
            if chosen_contact:
                p_action = self.pending_whatsapp_contact_choice
                self.pending_whatsapp_contact_choice = None
                action_type = p_action.get("pending_action")

                if action_type == "send_text":
                    msg = p_action.get("message", "")
                    ok, prep_msg = self.whatsapp_mgr.prepare_text_message(chosen_contact, msg)
                    if not ok:
                        return f"Message prepare karne mein issue aaya boss: {prep_msg}"
                    self.pending_whatsapp_confirmation = {
                        "type": "text",
                        "recipient": chosen_contact,
                        "message": msg
                    }
                    return f"Boss, {chosen_contact} ko ye message bhejane ke liye ready hoon:\n\"{msg}\"\nKya main send kar doon? Say 'Haan bhejo' to confirm ya 'Cancel' to abort."

                elif action_type == "send_file":
                    file_path = p_action.get("file_path")
                    filename = p_action.get("filename")
                    att_type = p_action.get("attachment_type", "document")
                    ok, prep_msg = self.whatsapp_mgr.prepare_file_attachment(chosen_contact, file_path, att_type)
                    if not ok:
                        return f"File attach karne mein issue aaya boss: {prep_msg}"
                    self.pending_whatsapp_confirmation = {
                        "type": "file",
                        "recipient": chosen_contact,
                        "file_path": file_path,
                        "filename": filename,
                        "attachment_type": att_type
                    }
                    return f"Boss, '{filename}' file {chosen_contact} ke liye ready kar di hai. Kya main send kar doon? Say 'Haan bhejo' to confirm ya 'Cancel' to abort."
            else:
                opts = "\n".join([f"{i+1}. {c}" for i, c in enumerate(contacts)])
                return f"Boss, kripya clearly number (jaise '1' ya 'pehla') ya contact ka naam batayein:\n{opts}"

        # 2. File Choice Selection
        if self.pending_whatsapp_file_choice:
            files = self.pending_whatsapp_file_choice["files"]
            file_names = [f.name for f in files]
            chosen_name = self._resolve_indexed_or_named_choice(text_lower, file_names)
            if chosen_name:
                target_file = next(f for f in files if f.name == chosen_name)
                recipient = self.pending_whatsapp_file_choice.get("recipient")
                att_type = self.pending_whatsapp_file_choice.get("attachment_type", "document")
                self.pending_whatsapp_file_choice = None

                # Search contact now that file is chosen
                ok_c, c_msg, matches = self.whatsapp_mgr.search_and_select_contact(recipient)
                if not ok_c and matches:
                    self.pending_whatsapp_contact_choice = {
                        "contacts": matches,
                        "pending_action": "send_file",
                        "file_path": str(target_file),
                        "filename": target_file.name,
                        "attachment_type": att_type
                    }
                    opts = "\n".join([f"{i+1}. {c}" for i, c in enumerate(matches)])
                    return f"Boss, '{recipient}' naam ke multiple contacts mile hain:\n{opts}\nKripya batayein kaunse contact ko bhejna hai?"
                elif not ok_c:
                    return f"Boss, {c_msg}"

                resolved_contact = matches[0] if matches else recipient
                ok_att, att_msg = self.whatsapp_mgr.prepare_file_attachment(resolved_contact, str(target_file), att_type)
                if not ok_att:
                    return f"Boss, attachment prepare karne mein issue aaya: {att_msg}"

                self.pending_whatsapp_confirmation = {
                    "type": "file",
                    "recipient": resolved_contact,
                    "file_path": str(target_file),
                    "filename": target_file.name,
                    "attachment_type": att_type
                }
                return f"Boss, '{target_file.name}' file {resolved_contact} ke liye ready kar di hai. Kya main send kar doon? Say 'Haan bhejo' to confirm ya 'Cancel' to abort."
            else:
                opts = "\n".join([f"{i+1}. {fn}" for i, fn in enumerate(file_names)])
                return f"Boss, kripya clearly number ya file ka naam batayein:\n{opts}"

        # 3. Missing Detail Clarification
        if self.pending_whatsapp_clarification:
            c_type = self.pending_whatsapp_clarification.get("type")
            if c_type == "recipient_for_text":
                msg = self.pending_whatsapp_clarification.get("message")
                self.pending_whatsapp_clarification = None
                rec = WhatsAppCommandParser._extract_recipient(text, text_lower) or text.strip()
                fake_cmd = {"action": "send_text", "recipient": rec, "message": msg, "raw": text}
                return self._handle_whatsapp_command(text, text_lower, lang, fake_cmd)
            elif c_type == "message_for_recipient":
                rec = self.pending_whatsapp_clarification.get("recipient")
                self.pending_whatsapp_clarification = None
                fake_cmd = {"action": "send_text", "recipient": rec, "message": text.strip(), "raw": text}
                return self._handle_whatsapp_command(text, text_lower, lang, fake_cmd)
            elif c_type == "recipient_for_file":
                f_name = self.pending_whatsapp_clarification.get("filename")
                f_hint = self.pending_whatsapp_clarification.get("folder_hint")
                att_t = self.pending_whatsapp_clarification.get("file_type")
                self.pending_whatsapp_clarification = None
                rec = WhatsAppCommandParser._extract_recipient(text, text_lower) or text.strip()
                fake_cmd = {"action": f"send_{att_t}", "recipient": rec, "filename": f_name, "folder_hint": f_hint, "attachment_type": att_t, "raw": text}
                return self._handle_whatsapp_command(text, text_lower, lang, fake_cmd)

        # 4. Final Send Confirmation
        if self.pending_whatsapp_confirmation:
            is_yes = any(w in text_lower for w in ["yes", "haan", "ha", "yep", "yeah", "confirm", "kar do", "theek hai", "sure", "bilkul", "bhejo", "send"])
            is_no = any(w in text_lower for w in ["no", "nahi", "nahin", "cancel", "mat karo", "rehne do", "don't"])

            if is_yes:
                self.pending_whatsapp_confirmation = None
                ok, send_res = self.whatsapp_mgr.send_confirmed_action()
                if ok:
                    return f"{random.choice(SARCASTIC_RESPONSES['whatsapp_sent'])}\n{send_res}"
                else:
                    return f"Boss, message bhejane mein issue aaya: {send_res}"
            elif is_no:
                self.pending_whatsapp_confirmation = None
                self.whatsapp_mgr.cancel_pending()
                return random.choice(SARCASTIC_RESPONSES["whatsapp_cancel"])
            else:
                p = self.pending_whatsapp_confirmation
                target = p.get("recipient", "contact")
                detail = p.get("message") if p.get("type") == "text" else p.get("filename")
                return f"Boss, {target} ko '{detail}' bhejane se pehle aapka confirmation zaroori hai. Say 'Haan bhejo' to send ya 'Cancel' to abort."

        return None

    def _handle_whatsapp_command(self, text: str, text_lower: str, lang: str, cmd: Dict[str, Any]) -> str:
        """Executes parsed WhatsApp commands for opening, texting, and sending documents/images."""
        action = cmd.get("action")

        if action == "open_whatsapp":
            ok, msg = self.whatsapp_mgr.open_whatsapp_web()
            return msg

        elif action == "check_status":
            st, msg = self.whatsapp_mgr.check_status()
            return f"WhatsApp Web Status: {msg}"

        elif action == "cancel":
            self.pending_whatsapp_confirmation = None
            self.pending_whatsapp_contact_choice = None
            self.pending_whatsapp_file_choice = None
            self.pending_whatsapp_clarification = None
            ok, msg = self.whatsapp_mgr.cancel_pending()
            return msg

        elif action == "send_text":
            recipient = cmd.get("recipient")
            message = cmd.get("message")

            if not recipient:
                self.pending_whatsapp_clarification = {"type": "recipient_for_text", "message": message}
                return "Boss, WhatsApp message kisko bhejna hai? Kripya contact ka naam ya number batao."

            if not message:
                self.pending_whatsapp_clarification = {"type": "message_for_recipient", "recipient": recipient}
                return f"Boss, {recipient} ko kya message likh kar bhejna hai?"

            # Ensure WhatsApp Web is running
            st, _ = self.whatsapp_mgr.check_status()
            if st == STATUS_DISCONNECTED:
                ok, o_msg = self.whatsapp_mgr.open_whatsapp_web()
                if not ok:
                    return f"WhatsApp Web open nahi ho paya boss: {o_msg}"

            st, _ = self.whatsapp_mgr.check_status()
            if st == STATUS_AWAITING_QR:
                return "Boss, WhatsApp Web open hai par aap logged in nahi hain. Kripya pehle phone se QR code scan kar lijiye!"

            # Search contact
            ok_c, c_msg, matches = self.whatsapp_mgr.search_and_select_contact(recipient)
            if not ok_c and matches:
                self.pending_whatsapp_contact_choice = {
                    "contacts": matches,
                    "pending_action": "send_text",
                    "message": message
                }
                opts = "\n".join([f"{i+1}. {c}" for i, c in enumerate(matches)])
                return f"Boss, '{recipient}' naam ke multiple contacts mile hain:\n{opts}\nKripya batayein kaunse contact ko bhejna hai?"
            elif not ok_c:
                return f"Boss, {c_msg}"

            resolved_contact = matches[0] if matches else recipient
            ok_prep, p_msg = self.whatsapp_mgr.prepare_text_message(resolved_contact, message)
            if not ok_prep:
                return f"Message prepare karne mein issue aaya boss: {p_msg}"

            self.pending_whatsapp_confirmation = {
                "type": "text",
                "recipient": resolved_contact,
                "message": message
            }
            return f"Boss, {resolved_contact} ko ye message bhejane ke liye ready hoon:\n\"{message}\"\nKya main send kar doon? Say 'Haan bhejo' to confirm ya 'Cancel' to abort."

        elif action in ["send_pdf", "send_image"]:
            recipient = cmd.get("recipient")
            filename = cmd.get("filename", "")
            folder_hint = cmd.get("folder_hint")
            att_type = cmd.get("attachment_type", "pdf")

            if not recipient:
                self.pending_whatsapp_clarification = {
                    "type": "recipient_for_file",
                    "filename": filename,
                    "folder_hint": folder_hint,
                    "file_type": att_type
                }
                return "Boss, ye file WhatsApp pe kisko bhejni hai? Contact ka naam ya number bataiye."

            # File verification in approved folders
            ok_f, f_msg, matched_files = resolve_whatsapp_file(filename, folder_hint, att_type)
            if not ok_f and matched_files:
                self.pending_whatsapp_file_choice = {
                    "files": matched_files,
                    "recipient": recipient,
                    "attachment_type": att_type
                }
                opts = "\n".join([f"{i+1}. {f.name}" for i, f in enumerate(matched_files)])
                return f"Boss, approved folders mein multiple matching files mili hain:\n{opts}\nKaunsi file bhejni hai?"
            elif not ok_f:
                prefix = "" if f_msg.lower().startswith("boss") else "Boss, "
                return f"{prefix}{f_msg}"

            target_file = matched_files[0]

            # Ensure WhatsApp Web is running
            st, _ = self.whatsapp_mgr.check_status()
            if st == STATUS_DISCONNECTED:
                ok, o_msg = self.whatsapp_mgr.open_whatsapp_web()
                if not ok:
                    return f"WhatsApp Web open nahi ho paya: {o_msg}"

            st, _ = self.whatsapp_mgr.check_status()
            if st == STATUS_AWAITING_QR:
                return "Boss, WhatsApp Web open ho gaya hai par aap logged in nahi hain. Kripya phone se QR code scan kar lijiye!"

            # Search contact
            ok_c, c_msg, matches = self.whatsapp_mgr.search_and_select_contact(recipient)
            if not ok_c and matches:
                self.pending_whatsapp_contact_choice = {
                    "contacts": matches,
                    "pending_action": "send_file",
                    "file_path": str(target_file),
                    "filename": target_file.name,
                    "attachment_type": att_type
                }
                opts = "\n".join([f"{i+1}. {c}" for i, c in enumerate(matches)])
                return f"Boss, '{recipient}' naam ke multiple contacts mile hain:\n{opts}\nKripya batayein kaunse contact ko bhejna hai?"
            elif not ok_c:
                return f"Boss, {c_msg}"

            resolved_contact = matches[0] if matches else recipient
            ok_att, att_msg = self.whatsapp_mgr.prepare_file_attachment(resolved_contact, str(target_file), att_type)
            if not ok_att:
                return f"Boss, attachment prepare karne mein issue aaya: {att_msg}"

            self.pending_whatsapp_confirmation = {
                "type": "file",
                "recipient": resolved_contact,
                "file_path": str(target_file),
                "filename": target_file.name,
                "attachment_type": att_type
            }
            return f"Boss, '{target_file.name}' file {resolved_contact} ke liye ready kar di hai. Kya main send kar doon? Say 'Haan bhejo' to confirm ya 'Cancel' to abort."

        return "Command samajh nahi aayi boss, WhatsApp ke baare mein kya karna hai?"

    def _resolve_indexed_or_named_choice(self, text_lower: str, choices: List[str]) -> Optional[str]:
        """Resolves natural language ordinal numbers or name matching from options list."""
        # 1. Number words & ordinals
        word_idx_map = {
            "1": 0, "first": 0, "pehla": 0, "pehli": 0, "one": 0, "ek": 0,
            "2": 1, "second": 1, "dusra": 1, "dusri": 1, "two": 1, "do": 1,
            "3": 2, "third": 2, "teesra": 2, "teesri": 2, "three": 2, "teen": 2,
            "4": 3, "fourth": 3, "chautha": 3, "four": 3, "char": 3,
            "5": 4, "fifth": 4, "paanchwa": 4, "five": 4, "panch": 4
        }
        for token in text_lower.replace(".", " ").replace(":", " ").split():
            if token in word_idx_map:
                idx = word_idx_map[token]
                if 0 <= idx < len(choices):
                    return choices[idx]

        # 2. Substring matching
        for c in choices:
            if c.lower() in text_lower:
                return c
            # Individual tokens of candidate in user input
            tokens = [t for t in c.lower().split() if len(t) > 2]
            if any(t in text_lower for t in tokens):
                return c

        return None

    def _handle_companion_command(self, text: str, text_lower: str, lang: str, cmd: dict) -> str:
        action = cmd.get("action")
        if action == "status":
            info = self.companion_mgr.get_pairing_info()
            if self.companion_mgr.is_phone_connected():
                return f"Boss, aapka phone ({info['device']}) Wi-Fi se connected hai! Main contacts search aur calls laga sakti hoon."
            else:
                return f"Boss, phone abhi disconnected hai. JARVIS Companion app kholkar Wi-Fi pairing PIN ({info['pin']}) enter kijiye. Laptop IP: {info['ip']}:{info['port']}."

        elif action == "call":
            recipient = cmd.get("recipient", "").strip()
            if not recipient:
                return "Boss, kripya batayein kisko call lagana hai? Jaise: 'Jarvis, mummy ko call lagao'."

            if not self.companion_mgr.is_phone_connected() and not self.companion_mgr._wait_for_phone_connection(max_wait=2.0):
                info = self.companion_mgr.get_pairing_info()
                return (
                    f"Boss, aapka Realme 10 Pro phone abhi connected nahi hai! "
                    f"Kripya phone par 'JARVIS Companion' app open karein aur Connect tap karein. "
                    f"Laptop IP: {info['ip']}, PIN: {info['pin']}."
                )

            # Check if recipient is purely phone digits
            clean_digits = re.sub(r'[\s\-\(\)]', '', recipient)
            if clean_digits.isdigit() or (clean_digits.startswith('+') and clean_digits[1:].isdigit()):
                ok, msg = self.companion_mgr.make_call(recipient, "Phone Number")
                if ok:
                    return f"Calling {recipient} on your Realme phone now, boss!"
                else:
                    return f"Boss, call lagane mein issue aaya: {msg}"

            # Search contact on phone via companion manager
            matches = self.companion_mgr.search_contact(recipient)
            if not matches:
                # Try relation alias fallbacks (e.g. mummy -> maa / mom, papa -> dad)
                for alias in self._get_contact_aliases(recipient):
                    matches = self.companion_mgr.search_contact(alias)
                    if matches:
                        break

            if not matches:
                return f"Boss, aapke phone contacts mein '{recipient}' naam se koi number nahi mila."

            best_match = self._pick_best_contact_match(recipient, matches)
            matched_name = best_match.get("name", recipient)
            matched_number = best_match.get("number", "")

            print(f"[Companion Call] Recipient query: '{recipient}' -> Best contact match: '{matched_name}' ({matched_number})")

            # Direct 1-shot calling without extra verbal confirmation
            ok, msg = self.companion_mgr.make_call(matched_number, matched_name)
            if ok:
                return f"Calling {matched_name} ({matched_number}) on your Realme phone now, boss!"
            else:
                return f"Boss, {matched_name} ko call lagane mein dikkat aayi: {msg}"

        return "Command samajh nahi aayi boss, phone ke baare mein kya karna hai?"

    def _get_contact_aliases(self, recipient: str) -> list:
        r = recipient.strip().lower()
        alias_dict = {
            "mummy": ["mom", "maa", "mother", "मम्मी", "माँ"],
            "mom": ["mummy", "maa", "mother", "मम्मी"],
            "maa": ["mummy", "mom", "mother", "मम्मी"],
            "papa": ["dad", "father", "पापा", "पिताजी"],
            "dad": ["papa", "father", "पापा"],
            "bhai": ["bhaiya", "bro", "brother", "भाई"],
            "bhaiya": ["bhai", "bro", "brother", "भैया"],
            "didi": ["sister", "sis", "दीदी"],
        }
        return alias_dict.get(r, [])

    def _pick_best_contact_match(self, recipient: str, matches: list) -> dict:
        if not matches:
            return {}
        if len(matches) == 1:
            return matches[0]

        q = recipient.strip().lower()
        scored = []
        for m in matches:
            name = m.get("name", "").strip().lower()
            if not name:
                continue

            # 1. Exact match (e.g. "Aman" == "aman")
            if name == q:
                score = 10000
            # 2. Exact word token match (e.g. "Aman Verma", "Aman Room")
            elif q in name.split():
                score = 5000 - len(name)
            # 3. Starts with query
            elif name.startswith(q):
                score = 3000 - len(name)
            # 4. Any word in contact starts with query
            elif any(w.startswith(q) for w in name.split()):
                score = 2000 - len(name)
            else:
                ratio = difflib.SequenceMatcher(None, q, name).ratio()
                score = int(ratio * 1000)

            scored.append((score, m))

        if not scored:
            return matches[0]

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]
