import re
from typing import Optional, Dict, Any, Tuple

class MemoryCommandParser:
    """
    Parses natural voice commands in English, Hindi, and Hinglish for JARVIS's
    Persistent Custom Q&A Memory System.
    """

    @classmethod
    def clean_text(cls, text: str) -> str:
        if not text:
            return ""
        return text.strip()

    @classmethod
    def parse(cls, raw_text: str) -> Optional[Dict[str, Any]]:
        """
        Analyze user input for memory-related management intents:
        - 'save'
        - 'retrieve'
        - 'update'
        - 'delete'
        - 'list'
        - 'search'

        Returns None if the command is not a memory management instruction.
        """
        text = cls.clean_text(raw_text)
        if not text:
            return None

        text_lower = text.lower()

        # ---------------------------------------------------------
        # 1. LIST COMMANDS
        # ---------------------------------------------------------
        list_patterns = [
            r'show\s+all\s+(my\s+)?(saved\s+)?(questions|memories|memory|q&a)',
            r'list\s+all\s+(my\s+)?(saved\s+)?(questions|memories)',
            r'maine\s+tumhe\s+kya\s*[- ]?kya\s+yaad\s+karwaya\s+hai',
            r'kya\s*[- ]?kya\s+yaad\s+hai\s+tumhe',
            r'show\s+saved\s+questions',
            r'saari\s+saved\s+memory\s+dikhao',
            r'saved\s+questions\s+dikhao',
            r'show\s+my\s+custom\s+memory',
        ]
        if any(re.search(p, text_lower) for p in list_patterns):
            return {"action": "list"}

        # ---------------------------------------------------------
        # 2. SAVE COMMANDS
        # ---------------------------------------------------------

        # Helper to clean extracted Q&A pairs
        def _clean_qa(q: str, a: str) -> dict:
            clean_q = re.sub(r'^(?:question\s*[:\-]\s*)', '', q.strip(" ?.,\"'"), flags=re.IGNORECASE).strip(" ?.,\"'")
            clean_a = re.sub(r'^(?:answer\s*[:\-]\s*)', '', a.strip(" ?.,\"'"), flags=re.IGNORECASE).strip(" ?.,\"'")
            return {"action": "save", "question": clean_q, "answer": clean_a}

        # Pattern: Question: ... Answer: ... (separated by ?, ., comma, or whitespace)
        m_qa = re.search(r'question\s*[:\-]\s*(.*?)[,\.\?\n\r\t]+\s*answer\s*[:\-]\s*(.*)', text, re.IGNORECASE)
        if m_qa:
            return _clean_qa(m_qa.group(1), m_qa.group(2))

        # Pattern: "Whenever I ask <Q>, (always)? (reply|answer|say) <A>"
        m_when = re.search(r'whenever\s+i\s+ask\s+(.*?)[,\.\?]?\s+(?:always\s+)?(?:reply|answer|say|bolo)\s+(.*)', text, re.IGNORECASE)
        if m_when:
            return _clean_qa(m_when.group(1), m_when.group(2))

        # Pattern: "If I ask <Q>, (always)? (reply|answer|say) <A>"
        m_if = re.search(r'if\s+i\s+ask\s+(.*?)[,\.\?]?\s+(?:always\s+)?(?:reply|answer|say|bolo)\s+(.*)', text, re.IGNORECASE)
        if m_if:
            return _clean_qa(m_if.group(1), m_if.group(2))

        # Pattern: "Remember this: If I ask <Q>, answer <A>"
        m_rem_if = re.search(r'remember\s+this\s*[:\-]?\s*(?:if\s+i\s+ask\s+)?(.*?)[,\.\?]?\s+(?:answer|reply|bolo)\s+(.*)', text, re.IGNORECASE)
        if m_rem_if and len(m_rem_if.groups()) >= 2 and m_rem_if.group(1) and m_rem_if.group(2):
            return _clean_qa(m_rem_if.group(1), m_rem_if.group(2))

        # Pattern: "is question ka answer yaad rakhna: <Q>? <A>"
        m_hi_rem = re.search(r'(?:is\s+question\s+ka\s+answer\s+yaad\s+rakhna|yaad\s+rakhna)\s*[:\-]?\s*(.*?\?)\s*(.*)', text, re.IGNORECASE)
        if m_hi_rem:
            return _clean_qa(m_hi_rem.group(1), m_hi_rem.group(2))

        # Pattern: "Remember this answer permanently: <Statement>"
        # e.g., "Remember this answer permanently: My college name is MMMUT Gorakhpur."
        m_perm = re.search(r'remember\s+this\s+(?:answer\s+)?permanently\s*[:\-]?\s*(.*)', text, re.IGNORECASE)
        if m_perm:
            statement = m_perm.group(1).strip(" ?.,\"'")
            # If statement has form "X is Y" or "X ka naam Y hai"
            m_is = re.search(r'^(.*?)\s+is\s+(.*)', statement, re.IGNORECASE)
            if m_is:
                subject = m_is.group(1).strip()
                ans = m_is.group(2).strip()
                q = f"What is {subject}?" if not subject.lower().startswith("what") else subject
                return _clean_qa(q, ans)
            return _clean_qa(statement, statement)

        # Pattern: "Save this in your memory: <Q>? <A>"
        m_save_mem = re.search(r'save\s+this\s+in\s+(?:your\s+)?memory\s*[:\.\-]?\s*(.*)', text, re.IGNORECASE)
        if m_save_mem:
            content = m_save_mem.group(1).strip()
            # If content has Question:... Answer:...
            m_sub_qa = re.search(r'question\s*[:\-]\s*(.*?)[,\.\?\n\r\t]+\s*answer\s*[:\-]\s*(.*)', content, re.IGNORECASE)
            if m_sub_qa:
                return _clean_qa(m_sub_qa.group(1), m_sub_qa.group(2))
            if '?' in content:
                parts = content.split('?', 1)
                return _clean_qa(parts[0], parts[1])
            elif ':' in content:
                parts = content.split(':', 1)
                return _clean_qa(parts[0], parts[1])

        # Pattern: Ambiguous / Prompt-to-save commands
        # "Jarvis, remember this question and answer."
        # "Isko apni permanent memory mein save kar lo."
        # "Save this answer for whenever I ask this question."
        ambiguous_save = [
            r'remember\s+this\s+question\s+and\s+answer',
            r'isko\s+apni\s+permanent\s+memory\s+mein\s+save\s+kar\s+lo',
            r'save\s+this\s+(answer\s+)?for\s+whenever\s+i\s+ask\s+this\s+question',
            r'save\s+this\s+in\s+memory',
            r'memory\s+mein\s+save\s+karo',
            r'permanent\s+memory\s+mein\s+save'
        ]
        if any(re.search(p, text_lower) for p in ambiguous_save):
            return {"action": "save_ambiguous", "raw_text": text}

        # ---------------------------------------------------------
        # 3. UPDATE COMMANDS
        # ---------------------------------------------------------
        # Pattern: "Jarvis, update the answer to my best-friend question to Amit."
        m_upd = re.search(r'update\s+(?:the\s+)?answer\s+(?:to|for)\s+(.*?)\s+(?:to|with|as)\s+(.*)', text, re.IGNORECASE)
        if m_upd:
            q_target = m_upd.group(1).strip(" ?.,\"'")
            # clean up "question" word if trailing
            q_target = re.sub(r'\s+question$', '', q_target, flags=re.IGNORECASE)
            return {
                "action": "update",
                "question": q_target,
                "new_answer": m_upd.group(2).strip(" ?.,\"'")
            }

        # Pattern: "Is question ka purana answer replace kar do"
        m_replace = re.search(r'(?:is\s+question\s+ka\s+)?(?:purana\s+)?answer\s+replace\s+kar\s+do\s*[:\-]?\s*(.*)', text, re.IGNORECASE)
        if m_replace:
            content = m_replace.group(1).strip()
            if '?' in content:
                parts = content.split('?', 1)
                return {"action": "update", "question": parts[0].strip(), "new_answer": parts[1].strip(" ?.,\"'")}
            return {"action": "update_ambiguous", "raw_text": text}

        # ---------------------------------------------------------
        # 4. DELETE / FORGET COMMANDS
        # ---------------------------------------------------------
        # Pattern: "Jarvis, forget the saved answer to <Q>"
        m_del1 = re.search(r'(?:forget|delete)\s+(?:the\s+)?(?:saved\s+)?(?:answer\s+to\s+|memory\s+for\s+|question\s+)?(.*)', text, re.IGNORECASE)
        if m_del1 and any(w in text_lower for w in ["forget", "delete"]):
            target = m_del1.group(1).strip(" ?.,\"'")
            if target and target.lower() not in ["this", "it", "that", ""]:
                return {"action": "delete", "question": target}

        # Pattern: "Meri custom memory se ye question delete kar do: <Q>"
        m_del2 = re.search(r'(?:meri\s+)?(?:custom\s+)?memory\s+se\s+(?:ye\s+)?(?:question\s+)?(?:delete|hata)\s+(?:kar\s+do|karo)\s*[:\-]?\s*(.*)', text, re.IGNORECASE)
        if m_del2:
            target = m_del2.group(1).strip(" ?.,\"'")
            if target:
                return {"action": "delete", "question": target}
            return {"action": "delete_ambiguous", "raw_text": text}

        # ---------------------------------------------------------
        # 5. RETRIEVE / SEARCH COMMANDS
        # ---------------------------------------------------------
        # "Jarvis, what answer did I save for this question: <Q>?"
        m_ret1 = re.search(r'what\s+answer\s+did\s+i\s+save\s+for\s+(?:this\s+question\s*[:\-]?)?\s*(.*)', text, re.IGNORECASE)
        if m_ret1:
            q_target = m_ret1.group(1).strip(" ?.,\"'")
            return {"action": "retrieve", "question": q_target if q_target else "last_context"}

        # "Maine tumhe iske baare mein kya yaad karwaya tha"
        m_ret2 = re.search(r'maine\s+tumhe\s+(?:is(?:ke)?\s+baare\s+mein\s+)?kya\s+yaad\s+karwaya\s+tha\s*[:\-]?\s*(.*)', text, re.IGNORECASE)
        if m_ret2:
            q_target = m_ret2.group(1).strip(" ?.,\"'")
            return {"action": "retrieve", "question": q_target if q_target else "last_context"}

        # "Jarvis, search my memory for the answer about <Topic>"
        m_search = re.search(r'search\s+(?:my\s+)?memory\s+(?:for\s+(?:the\s+)?(?:answer\s+about\s+)?)?\s*(.*)', text, re.IGNORECASE)
        if m_search and "memory" in text_lower:
            topic = m_search.group(1).strip(" ?.,\"'")
            return {"action": "search", "topic": topic}

        return None
