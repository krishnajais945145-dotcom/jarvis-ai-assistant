"""
Phone Companion Command Parser
Parses natural language commands for making phone calls and querying companion status.
Handles Hindi, Hinglish, and English voice/text commands.
"""

import re
from typing import Optional, Dict


def _clean_recipient(raw: str) -> str:
    cleaned = raw.strip()
    # Strip polite prefixes
    cleaned = re.sub(r'^(?:please\s+|kripya\s+|zara\s+|ek\s+baar\s+)', '', cleaned, flags=re.IGNORECASE).strip()
    # Strip device qualifiers
    cleaned = re.sub(r'\b(?:on|from|via|through)\s+(?:my\s+)?(?:realme\s+)?(?:phone|mobile)\b', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'\b(?:mere\s+)?(?:realme\s+)?(?:phone|mobile)\s+se\b', '', cleaned, flags=re.IGNORECASE).strip()
    # Strip redundant leading call/dial tokens
    cleaned = re.sub(r'^(?:call|phone|dial)\s+(?:to\s+)?', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'\b(?:ko|par|pe)\b$', '', cleaned).strip()
    # Strip trailing call/verb phrases if captured accidentally
    cleaned = re.sub(r'\s+(?:ko\s+)?(?:call|phone)\s+(?:lagao|lgao|lga\s+do|lga\s+de|lga|laga\s+do|laga\s+de|laga|karo|kro|kr\s+do|kr\s+de|kar\s+do|milao|mila\s+do|karna|lagana).*$', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'\b(?:ko|par|pe)\b$', '', cleaned).strip()
    return cleaned.strip()


class CompanionCallParser:
    @staticmethod
    def parse(text: str) -> Optional[Dict[str, str]]:
        if not text:
            return None

        clean_text = text.strip()
        # Remove polite prefixes/greetings e.g. "Jarvis", "Hey Jarvis", "Sun"
        clean_text = re.sub(r'^(?:hey\s+|hello\s+)?jarvis[,:\s]*', '', clean_text, flags=re.IGNORECASE).strip()
        text_lower = clean_text.lower()

        # 1. Status / Connectivity queries
        status_patterns = [
            r'^(?:phone|companion|realme|mobile)\s+(?:connected\s+hai|status\s+kya\s+hai|status|connect\s+hai\s+kya)',
            r'^(?:is\s+phone\s+connected|phone\s+status|companion\s+status)',
            r'^phone\s+connect\s+hua\s+kya'
        ]
        for pat in status_patterns:
            if re.search(pat, text_lower):
                return {"action": "status"}

        # 2. Call commands in Hindi / Hinglish:
        # e.g. "aman ko call lagao", "aman ko call lga do", "papa ko phone karo", "rahul ko call milao"
        m1 = re.search(r'(.+?)\s+ko\s+(?:phone|call)\s+(?:lagao|lgao|lga\s+do|lga\s+de|lga|laga\s+do|laga\s+de|laga|karo|kro|kr\s+do|kr\s+de|kar\s+do|milao|mila\s+do|karna|lagana|karna\s+hai|lagana\s+hai|lagayein|lagayen|lagaye|karein|karen|ghuma|ghumao)', text_lower)
        if m1:
            recipient = _clean_recipient(m1.group(1))
            if recipient:
                return {"action": "call", "recipient": recipient}

        # e.g. "call lagao aman ko" / "call lga do mummy ko" / "phone milao papa ko"
        m2 = re.search(r'(?:call|phone)\s+(?:lagao|lgao|lga\s+do|lga\s+de|lga|laga\s+do|laga\s+de|laga|karo|kro|kr\s+do|kr\s+de|kar\s+do|milao|mila\s+do|karna|lagana)\s+(?:to\s+)?(.+?)(?:\s+ko)?$', text_lower)
        if m2:
            recipient = _clean_recipient(m2.group(1))
            if recipient:
                return {"action": "call", "recipient": recipient}

        # e.g. "aman ko call", "mummy ko phone"
        m3 = re.search(r'^(.+?)\s+ko\s+(?:phone|call)$', text_lower)
        if m3:
            recipient = _clean_recipient(m3.group(1))
            if recipient:
                return {"action": "call", "recipient": recipient}

        # e.g. "make a call to Aman", "call mummy", "dial papa"
        m4 = re.search(r'^(?:make\s+a\s+call\s+to|make\s+call\s+to|call\s+to|call|phone|dial)\s+(.+)$', text_lower)
        if m4:
            raw_rec = m4.group(1).strip()
            # Avoid matching WhatsApp voice/video calls if explicitly requested
            if "whatsapp" in raw_rec:
                return None
            recipient = _clean_recipient(raw_rec)
            if recipient:
                return {"action": "call", "recipient": recipient}

        return None
