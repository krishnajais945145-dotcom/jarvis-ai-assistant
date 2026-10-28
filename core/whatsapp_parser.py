import re
from typing import Optional, Dict, Any

NON_RECIPIENT_WORDS = {
    "whatsapp", "whasstap", "whatsap", "watsapp", "watssap", "whtsapp", "whatsaap", "whatapp",
    "jarvis", "kisi", "sab", "isse", "isko", "usko", "ye", "yeh", "this", "that", "which", "web",
    "image", "photo", "pic", "tasveer", "pdf", "file", "document", "screenshot", "video",
    "folder", "desktop", "downloads", "documents", "pictures", "link", "message", "msg"
}

class WhatsAppCommandParser:
    """
    Parses Hindi, Hinglish, and English voice/text commands for WhatsApp Web automation.
    Extracts action, recipient, message text, filename/query, folder hint, and attachment type.
    """

    @classmethod
    def _normalize_text(cls, text_lower: str) -> str:
        """Normalizes common typos, phonetic spelling variations, and spacing."""
        # 1. WhatsApp typos
        norm = re.sub(r'\b(whasstap|whatsap|watsapp|watssap|whtsapp|whatsaap|wahtsapp|watsap|whatapp|whats\s*app)\b', 'whatsapp', text_lower)
        # 2. Folder typos & spaced compound words
        norm = re.sub(r'\bdesk\s*top\b', 'desktop', norm)
        norm = re.sub(r'\bscreen\s*shot(s)?\b', 'screenshot', norm)
        norm = re.sub(r'\bdown\s*load(s)?\b', 'downloads', norm)
        norm = re.sub(r'\bdoc\s*ument(s)?\b', 'documents', norm)
        norm = re.sub(r'\bpic\s*ture(s)?\b', 'pictures', norm)
        # 3. Repeated typing/speech letters in common action verbs
        norm = re.sub(r'\bsend+d+\b', 'send', norm)
        norm = re.sub(r'\bbhej+j*o*\b', 'bhejo', norm)
        norm = re.sub(r'\bop+en+\b', 'open', norm)
        norm = re.sub(r'\bkhol+l*o*\b', 'kholo', norm)
        return norm

    @classmethod
    def parse(cls, raw_text: str) -> Optional[Dict[str, Any]]:
        if not raw_text or not raw_text.strip():
            return None

        text = raw_text.strip()
        text_lower = text.lower()
        text_norm = cls._normalize_text(text_lower)

        # 1. Cancel commands (e.g. "Cancel whatsapp", "Mat bhejo", "Ruk jao", "WhatsApp message cancel karo")
        if any(w in text_norm for w in ["cancel", "mat bhejo", "ruk jao", "rehne do", "don't send", "abort"]):
            return {
                "action": "cancel",
                "raw": text
            }

        # Check for WhatsApp or sharing intents
        has_whatsapp = "whatsapp" in text_norm or "wa" in text_norm.split()
        has_send_intent = any(w in text_norm for w in ["bhej", "send", "share", "forward", "kar do", "likho", "kholo", "open"])
        has_file_kw = any(w in text_norm for w in [".pdf", "pdf", "assignment", "report", "photo", "image", "pic", "tasveer", "screenshot", ".png", ".jpg", ".jpeg"])

        # If it doesn't mention whatsapp AND doesn't have send_intent + file_kw, skip
        if not has_whatsapp and not (has_send_intent and has_file_kw):
            return None

        # 2. Status check commands
        if has_whatsapp and any(w in text_norm for w in ["status", "connected", "logged in", "login hai", "check karo"]):
            return {
                "action": "check_status",
                "raw": text
            }

        # 3. Open WhatsApp commands
        open_patterns = [
            r'whatsapp\s+(web\s+)?(kholo|open\s+kar\s+do|open\s+karo|open|launch|chalu\s+karo)',
            r'(kholo|open|launch)\s+whatsapp(\s+web)?',
            r'whatsapp\s+pe\s+message\s+bhejna\s+hai',
            r'open\s+whatsapp\s+web'
        ]
        if any(re.search(pat, text_norm) for pat in open_patterns):
            # Only open if no recipient or file attachment is specified
            if not any(k in text_norm for k in [":", "assignment", "report", ".pdf", "photo", "image", "screenshot", "kal", "main", "mein"]):
                rec = cls._extract_recipient(text, text_norm)
                if not rec:
                    return {
                        "action": "open_whatsapp",
                        "raw": text
                    }

        # 4. Folder hint extraction
        folder_hint = None
        for f in ["downloads", "desktop", "documents", "pictures", "screenshots"]:
            if f in text_norm:
                folder_hint = f
                break

        # 5. PDF & Document attachment commands
        is_pdf_cmd = any(w in text_norm for w in [".pdf", "pdf", "assignment", "report", "document", "doc", "marksheet", "resume", "cv"])
        is_image_cmd = any(w in text_norm for w in ["photo", "image", "pic", "tasveer", "screenshot", "wallpaper", ".png", ".jpg", ".jpeg"])

        if is_pdf_cmd:
            parsed = cls._parse_pdf_command(text, text_norm, folder_hint)
            if parsed:
                return parsed

        # 6. Image attachment commands
        if is_image_cmd:
            parsed = cls._parse_image_command(text, text_norm, folder_hint)
            if parsed:
                return parsed

        # 7. Text Message commands
        parsed_text = cls._parse_text_message_command(text, text_norm)
        if parsed_text:
            return parsed_text

        return None

    @classmethod
    def _parse_pdf_command(cls, text: str, text_lower: str, folder_hint: Optional[str]) -> Optional[Dict[str, Any]]:
        recipient = cls._extract_recipient(text, text_lower)
        
        pdf_match = re.search(r'([A-Za-z0-9_\-]+\.pdf)', text, re.IGNORECASE)
        if pdf_match:
            filename = pdf_match.group(1).strip()
        else:
            if any(w in text_lower for w in ["ye pdf", "yeh pdf", "this pdf", "is pdf", "the pdf"]):
                filename = "latest.pdf"
            else:
                named_match = re.search(r'(?:se|from|folder se)?\s*([A-Za-z0-9_\-]+)\s*(?:pdf|document|marksheet|report|resume)', text_lower)
                if named_match and named_match.group(1).strip() not in NON_RECIPIENT_WORDS:
                    filename = named_match.group(1).strip() + ".pdf"
                else:
                    filename = "document.pdf"

        return {
            "action": "send_pdf",
            "recipient": recipient,
            "filename": filename,
            "folder_hint": folder_hint,
            "attachment_type": "pdf",
            "raw": text
        }

    @classmethod
    def _parse_image_command(cls, text: str, text_lower: str, folder_hint: Optional[str]) -> Optional[Dict[str, Any]]:
        recipient = cls._extract_recipient(text, text_lower)
        
        img_match = re.search(r'([A-Za-z0-9_\-]+\.(?:png|jpg|jpeg|webp))', text, re.IGNORECASE)
        if img_match:
            filename = img_match.group(1).strip()
        elif "screenshot" in text_lower:
            filename = "screenshot.png"
        elif any(w in text_lower for w in ["meri photo", "my photo"]):
            filename = "meri_photo.png"
        elif any(w in text_lower for w in ["ye image", "is image", "this image", "wali image", "wali photo", "photo", "image", "pic"]):
            filename = "latest_image.png"
        else:
            filename = "photo.png"

        return {
            "action": "send_image",
            "recipient": recipient,
            "filename": filename,
            "folder_hint": folder_hint,
            "attachment_type": "image",
            "raw": text
        }

    @classmethod
    def _parse_text_message_command(cls, text: str, text_lower: str) -> Optional[Dict[str, Any]]:
        recipient = cls._extract_recipient(text, text_lower)
        message = ""

        # Pattern 1: Explicit colon: "... bhejo: <message>" or "... message: <message>"
        if ":" in text:
            parts = text.split(":", 1)
            message = parts[1].strip()

        # Pattern 2: "likho ki <message>" or "likho <message>"
        elif "likho ki" in text_lower or "likho" in text_lower:
            m = re.search(r'likho\s+(?:ki\s+)?(.+)', text, re.IGNORECASE)
            if m:
                message = m.group(1).strip()

        # Pattern 3: "... bhejo <message>"
        elif "bhejo" in text_lower:
            m = re.search(r'bhejo\s+(.+)', text, re.IGNORECASE)
            if m:
                message = m.group(1).strip()

        # Pattern 4: "saying <message>" or "that <message>"
        elif "saying" in text_lower or "that" in text_lower:
            m = re.search(r'(?:saying|that)\s+(.+)', text, re.IGNORECASE)
            if m:
                message = m.group(1).strip()

        # Clean trailing commands if message caught them
        for suffix in ["send kar do", "bhej do", "please"]:
            if message.lower().endswith(suffix):
                message = message[: -len(suffix)].strip()

        if recipient or message:
            return {
                "action": "send_text",
                "recipient": recipient,
                "message": message,
                "raw": text
            }
        return None

    @classmethod
    def _extract_recipient(cls, text: str, text_lower: str) -> Optional[str]:
        """Extracts contact recipient name or phone number from various Hindi/English syntax forms."""
        # 1. Explicit phone number (+91... or 10 digits)
        phone_match = re.search(r'(\+?\d{10,13})', text)
        if phone_match:
            return phone_match.group(1).strip()

        # 2. Hindi/Hinglish pattern: "whatsapp pe <Recipient> ko" or "whatsapp par <Recipient> ko"
        wa_ko_match = re.search(r'whatsapp\s+(?:pe|par)\s+([A-Za-z0-9_]+)\s+ko', text, re.IGNORECASE)
        if wa_ko_match:
            cand = wa_ko_match.group(1).strip()
            if cand.lower() not in NON_RECIPIENT_WORDS:
                return cand

        # 3. Pattern: "<Recipient> ko WhatsApp" or "<Recipient> ko bhej do" or "<Recipient> ko send kar do"
        ko_matches = re.finditer(r'([A-Za-z0-9_]+)\s+ko\b', text)
        for m in ko_matches:
            cand = m.group(1).strip()
            if cand.lower() not in NON_RECIPIENT_WORDS:
                return cand

        # 4. English pattern: "to <Recipient>"
        to_matches = re.finditer(r'\bto\s+([A-Za-z0-9_]+)', text, re.IGNORECASE)
        for tm in to_matches:
            cand = tm.group(1).strip()
            if cand.lower() not in NON_RECIPIENT_WORDS:
                return cand

        # 5. English pattern: "send/forward <Recipient> [the] <file>"
        send_to_match = re.search(r'\b(?:send|forward|share)\s+([A-Za-z0-9_]+)\s+(?:the\s+)?(?:image|photo|pic|file|pdf|assignment|doc|report|screenshot)', text, re.IGNORECASE)
        if send_to_match:
            cand = send_to_match.group(1).strip()
            if cand.lower() not in NON_RECIPIENT_WORDS:
                return cand

        # 6. English pattern: "with <Recipient>"
        with_match = re.search(r'\bwith\s+([A-Za-z0-9_]+)', text, re.IGNORECASE)
        if with_match:
            cand = with_match.group(1).strip()
            if cand.lower() not in NON_RECIPIENT_WORDS:
                return cand

        return None
