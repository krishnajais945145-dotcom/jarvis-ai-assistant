import os
import re
import json
import uuid
import shutil
import sqlite3
import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Tuple, List, Dict, Any

class JarvisMemoryManager:
    """
    Persistent Question-and-Answer Memory System for JARVIS.
    Stores custom question-answer pairs in a local SQLite database in the
    user's application data directory, surviving reboots and updates.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            local_appdata = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
            self.db_path = Path(local_appdata) / "JarvisAssistant" / "memory" / "jarvis_memory.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._init_database()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Create tables and indexes with safe backup before migration."""
        if self.db_path.exists() and self.db_path.stat().st_size > 0:
            self._create_auto_backup()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS custom_qa_memory (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    normalized_question TEXT NOT NULL,
                    canonical_question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed_at TEXT,
                    is_deleted INTEGER DEFAULT 0
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_qa_normalized ON custom_qa_memory(normalized_question)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_qa_canonical ON custom_qa_memory(canonical_question)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_qa_deleted ON custom_qa_memory(is_deleted)")
            conn.commit()

    def _create_auto_backup(self) -> Optional[str]:
        """Safely create an automatic backup of the database before modifications."""
        try:
            if not self.db_path.exists() or self.db_path.stat().st_size == 0:
                return None
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"jarvis_memory_backup_{ts}.db"
            shutil.copy2(str(self.db_path), str(backup_file))

            # Keep only the last 10 backups to save space
            backups = sorted(self.backup_dir.glob("jarvis_memory_backup_*.db"))
            if len(backups) > 10:
                for old_b in backups[:-10]:
                    try:
                        old_b.unlink()
                    except Exception:
                        pass
            return str(backup_file)
        except Exception as e:
            print(f"[MemoryManager] Auto backup notice: {e}")
            return None

    # -------------------------------------------------------------
    # Text Normalization & Multilingual Intent Canonicalization
    # -------------------------------------------------------------

    @staticmethod
    def normalize_text(text: str) -> str:
        """Strip punctuation, excessive whitespaces, and lowercase text."""
        if not text:
            return ""
        # Remove punctuation except alphanumeric and spaces
        cleaned = re.sub(r'[^\w\s\u0900-\u097F]', ' ', text.lower())
        return ' '.join(cleaned.split())

    @classmethod
    def canonicalize_question(cls, text: str) -> str:
        """
        Normalize and canonicalize question concepts across English, Hindi, and Hinglish.
        Strips conversational prefixes, filler question tags, and maps synonyms.
        """
        norm = cls.normalize_text(text)
        if not norm:
            return ""

        # Conversational filler prefixes to remove
        prefixes = [
            r'^(hey\s+)?jarvis\s*,?\s*',
            r'^(suno\s+)?jarvis\s*,?\s*',
            r'^arre\s+jarvis\s*,?\s*',
            r'^tell\s+me\s*,?\s*',
            r'^can\s+you\s+tell\s+me\s*,?\s*',
            r'^please\s+tell\s+me\s*,?\s*',
            r'^batao\s*(mujhe)?\s*,?\s*',
            r'^mujhe\s+batao\s*,?\s*',
            r'^kya\s+tum\s+bata\s+sakti\s+ho\s*,?\s*',
            r'^what\s+is\s+(my\s+)?',
            r'^who\s+is\s+(my\s+)?',
            r'^which\s+is\s+(my\s+)?',
            r'^where\s+is\s+(my\s+)?',
            r'^do\s+you\s+know\s+(who|what)\s+(is\s+)?(my\s+)?',
        ]
        res = norm
        for p in prefixes:
            res = re.sub(p, '', res).strip()

        # Concept synonyms map for robust cross-lingual matching
        synonym_map = {
            # Friends / Relationships
            "bestie": "best friend",
            "besty": "best friend",
            "jigri dost": "best friend",
            "pakka dost": "best friend",
            "dost": "friend",
            # Possessives
            "mera": "my",
            "meri": "my",
            "mere": "my",
            "apna": "my",
            "apni": "my",
            "apne": "my",
            # Questions & verbs
            "kaun hai": "who",
            "kon hai": "who",
            "kya hai": "what",
            "kaha hai": "where",
            "kab hai": "when",
            "kaun": "who",
            "kon": "who",
            "kya": "what",
            # Attributes
            "pasandida rang": "favourite colour",
            "pasandida": "favourite",
            "pasand ka": "favourite",
            "favorite": "favourite",
            "color": "colour",
            "rang": "colour",
            "naam": "name",
            "shahar": "city",
            "sehar": "city",
            "gaadi": "car",
            "project ka naam": "project name",
            "college ka naam": "college name",
        }

        # Substitute whole-phrase or word matches
        for src, target in synonym_map.items():
            pattern = rf'\b{re.escape(src)}\b'
            res = re.sub(pattern, target, res)

        # Standardize "who is my best friend" forms
        # e.g., "my best friend who" -> "who my best friend" -> "my best friend"
        tokens = [t for t in res.split() if t not in ["hai", "is", "the", "a", "an", "ka", "ki", "ke", "ko", "se", "who", "what"]]
        return ' '.join(tokens)

    @classmethod
    def extract_semantic_tokens(cls, text: str) -> set:
        """Extract high-value non-stopword tokens for semantic comparison."""
        canonical = cls.canonicalize_question(text)
        words = canonical.split()
        stopwords = {
            "is", "are", "was", "were", "the", "a", "an", "in", "on", "at", "to", "for",
            "hai", "ho", "tha", "thi", "the", "ka", "ki", "ke", "ko", "se", "me", "mein", "par", "pe",
            "batao", "bolo", "tell", "say", "know", "answer", "question"
        }
        return {w for w in words if w not in stopwords and len(w) > 1}

    # -------------------------------------------------------------
    # Memory CRUD Operations
    # -------------------------------------------------------------

    def save_memory(self, question: str, answer: str, category: str = "general", allow_overwrite: bool = False) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Save a question and exact answer to the persistent database.
        Returns (success, memory_dict, message_code).
        Avoids duplicates unless allow_overwrite is True.
        """
        clean_q = question.strip()
        clean_a = answer.strip()
        if not clean_q or not clean_a:
            return False, None, "INVALID_INPUT"

        norm_q = self.normalize_text(clean_q)
        canon_q = self.canonicalize_question(clean_q)

        now = datetime.datetime.now().isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Check for existing duplicate by normalized or canonical question
            cursor.execute("""
                SELECT * FROM custom_qa_memory
                WHERE is_deleted = 0 AND (normalized_question = ? OR canonical_question = ?)
            """, (norm_q, canon_q))
            existing = cursor.fetchone()

            if existing:
                existing_dict = dict(existing)
                if not allow_overwrite:
                    return False, existing_dict, "DUPLICATE_EXISTS"
                else:
                    # Update existing record
                    cursor.execute("""
                        UPDATE custom_qa_memory
                        SET question = ?, normalized_question = ?, canonical_question = ?, answer = ?, category = ?, updated_at = ?
                        WHERE id = ?
                    """, (clean_q, norm_q, canon_q, clean_a, category, now, existing_dict["id"]))
                    conn.commit()
                    cursor.execute("SELECT * FROM custom_qa_memory WHERE id = ?", (existing_dict["id"],))
                    updated = dict(cursor.fetchone())
                    return True, updated, "UPDATED_EXISTING"

            # Create new memory
            mem_id = f"mem_{uuid.uuid4().hex[:12]}"
            cursor.execute("""
                INSERT INTO custom_qa_memory (
                    id, question, normalized_question, canonical_question, answer,
                    category, created_at, updated_at, access_count, is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
            """, (mem_id, clean_q, norm_q, canon_q, clean_a, category, now, now))
            conn.commit()

            cursor.execute("SELECT * FROM custom_qa_memory WHERE id = ?", (mem_id,))
            new_row = dict(cursor.fetchone())
            return True, new_row, "SAVED_SUCCESSFULLY"

    def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM custom_qa_memory WHERE id = ? AND is_deleted = 0", (memory_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_memory(self, memory_id: str, new_answer: str, new_question: Optional[str] = None) -> Tuple[bool, str]:
        """Update an existing memory answer and optionally question."""
        clean_a = new_answer.strip()
        if not clean_a:
            return False, "Answer cannot be empty."

        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM custom_qa_memory WHERE id = ? AND is_deleted = 0", (memory_id,))
            row = cursor.fetchone()
            if not row:
                return False, f"Memory ID '{memory_id}' not found."

            if new_question and new_question.strip():
                clean_q = new_question.strip()
                norm_q = self.normalize_text(clean_q)
                canon_q = self.canonicalize_question(clean_q)
                cursor.execute("""
                    UPDATE custom_qa_memory
                    SET question = ?, normalized_question = ?, canonical_question = ?, answer = ?, updated_at = ?
                    WHERE id = ?
                """, (clean_q, norm_q, canon_q, clean_a, now, memory_id))
            else:
                cursor.execute("""
                    UPDATE custom_qa_memory
                    SET answer = ?, updated_at = ?
                    WHERE id = ?
                """, (clean_a, now, memory_id))
            conn.commit()
            return True, "Memory updated successfully."

    def delete_memory(self, memory_id: str, hard_delete: bool = False) -> Tuple[bool, str]:
        """Safely delete a memory (soft-delete by default to prevent accidental data loss)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM custom_qa_memory WHERE id = ? AND is_deleted = 0", (memory_id,))
            row = cursor.fetchone()
            if not row:
                return False, f"Memory ID '{memory_id}' not found."

            if hard_delete:
                cursor.execute("DELETE FROM custom_qa_memory WHERE id = ?", (memory_id,))
            else:
                now = datetime.datetime.now().isoformat()
                cursor.execute("UPDATE custom_qa_memory SET is_deleted = 1, updated_at = ? WHERE id = ?", (now, memory_id))
            conn.commit()
            return True, "Memory deleted successfully."

    def list_all_memories(self, search_term: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all active saved memories with optional search filtering."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if search_term and search_term.strip():
                q = f"%{search_term.strip().lower()}%"
                cursor.execute("""
                    SELECT * FROM custom_qa_memory
                    WHERE is_deleted = 0 AND (
                        LOWER(question) LIKE ? OR LOWER(answer) LIKE ? OR LOWER(canonical_question) LIKE ?
                    )
                    ORDER BY updated_at DESC
                """, (q, q, q))
            else:
                cursor.execute("""
                    SELECT * FROM custom_qa_memory
                    WHERE is_deleted = 0
                    ORDER BY updated_at DESC
                """)
            return [dict(r) for r in cursor.fetchall()]

    def get_memory_count(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM custom_qa_memory WHERE is_deleted = 0")
            return cursor.fetchone()[0]

    def record_access(self, memory_id: str):
        """Update access count and last accessed timestamp for a memory."""
        try:
            now = datetime.datetime.now().isoformat()
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE custom_qa_memory
                    SET access_count = access_count + 1, last_accessed_at = ?
                    WHERE id = ?
                """, (now, memory_id))
                conn.commit()
        except Exception:
            pass

    # -------------------------------------------------------------
    # High-Reliability Search & Multilingual Matching Engine
    # -------------------------------------------------------------

    def match_question(self, query: str, threshold: float = 0.65) -> Tuple[Optional[Dict[str, Any]], float, List[Dict[str, Any]]]:
        """
        Match an incoming query against saved custom memories.
        Supports English, Hindi, and Hinglish wording variations.
        
        Returns:
            (best_match, confidence_score, ambiguous_matches_list)
        """
        clean_q = query.strip()
        if not clean_q:
            return None, 0.0, []

        norm_query = self.normalize_text(clean_q)
        canon_query = self.canonicalize_question(clean_q)
        query_tokens = self.extract_semantic_tokens(clean_q)

        all_memories = self.list_all_memories()
        if not all_memories:
            return None, 0.0, []

        scored_matches = []

        for mem in all_memories:
            saved_norm = mem.get("normalized_question", "")
            saved_canon = mem.get("canonical_question", "")
            saved_tokens = self.extract_semantic_tokens(mem.get("question", ""))

            score = 0.0

            # 1. Exact raw or normalized match
            if norm_query == saved_norm:
                score = 1.0
            # 2. Canonical exact match (e.g. "who is my best friend" vs "mera best friend kaun hai")
            elif canon_query and saved_canon and canon_query == saved_canon:
                score = 0.98
            # 3. Canonical substring containment
            elif canon_query and saved_canon and (canon_query in saved_canon or saved_canon in canon_query):
                # Length ratio penalizes matching one short common word
                min_len = min(len(canon_query), len(saved_canon))
                max_len = max(len(canon_query), len(saved_canon))
                len_ratio = min_len / max_len if max_len > 0 else 0
                if len_ratio >= 0.5:
                    score = 0.85 + (0.10 * len_ratio)
                else:
                    score = 0.50 * len_ratio
            else:
                # 4. Token Overlap (Jaccard + Inclusion)
                if query_tokens and saved_tokens:
                    intersection = query_tokens.intersection(saved_tokens)
                    union = query_tokens.union(saved_tokens)
                    jaccard = len(intersection) / len(union) if union else 0.0
                    inclusion = len(intersection) / len(saved_tokens) if saved_tokens else 0.0

                    # If all key saved tokens are in query (e.g. "best", "friend")
                    if inclusion == 1.0:
                        score = 0.85 + (0.10 * jaccard)
                    elif jaccard >= 0.5:
                        score = 0.70 + (0.20 * jaccard)
                    else:
                        score = jaccard * 0.65

            # Require that at least one key subject word overlaps to prevent false positives
            if score >= threshold:
                if query_tokens and saved_tokens:
                    if not query_tokens.intersection(saved_tokens) and canon_query != saved_canon:
                        score = 0.0

            if score >= threshold:
                scored_matches.append((score, mem))

        if not scored_matches:
            return None, 0.0, []

        # Sort descending by score
        scored_matches.sort(key=lambda x: x[0], reverse=True)
        top_score, top_mem = scored_matches[0]

        # Check for ambiguity: multiple memories with close scores
        ambiguous = []
        if len(scored_matches) > 1:
            for s, m in scored_matches[1:]:
                # If another memory is within 0.08 score and >= threshold
                if (top_score - s) <= 0.08 and s >= threshold:
                    ambiguous.append(m)

        if ambiguous:
            all_amb = [top_mem] + ambiguous
            return None, top_score, all_amb

        return top_mem, top_score, []

    # -------------------------------------------------------------
    # Backup Export & Import
    # -------------------------------------------------------------

    def export_backup(self, target_path: Optional[str] = None) -> Tuple[bool, str]:
        """Export all active memories to a JSON backup file."""
        try:
            memories = self.list_all_memories()
            if not target_path:
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                target_path = str(self.backup_dir / f"jarvis_memory_export_{ts}.json")

            data = {
                "version": 1,
                "exported_at": datetime.datetime.now().isoformat(),
                "count": len(memories),
                "memories": memories
            }
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True, target_path
        except Exception as e:
            return False, str(e)

    def import_backup(self, source_path: str, merge: bool = True) -> Tuple[bool, int, str]:
        """
        Import memories from a JSON backup file.
        If merge is False, existing active memories will be archived first.
        """
        try:
            src = Path(source_path)
            if not src.exists():
                return False, 0, f"File not found: {source_path}"

            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)

            mem_list = data.get("memories", [])
            if not mem_list:
                return False, 0, "No memories found in backup file."

            self._create_auto_backup()

            imported_count = 0
            with self._get_connection() as conn:
                cursor = conn.cursor()
                if not merge:
                    cursor.execute("UPDATE custom_qa_memory SET is_deleted = 1 WHERE is_deleted = 0")

                for m in mem_list:
                    q = m.get("question", "").strip()
                    a = m.get("answer", "").strip()
                    if not q or not a:
                        continue
                    norm_q = self.normalize_text(q)
                    canon_q = self.canonicalize_question(q)
                    now = datetime.datetime.now().isoformat()
                    mem_id = m.get("id") or f"mem_{uuid.uuid4().hex[:12]}"

                    cursor.execute("""
                        INSERT OR REPLACE INTO custom_qa_memory (
                            id, question, normalized_question, canonical_question, answer,
                            category, created_at, updated_at, access_count, is_deleted
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                    """, (mem_id, q, norm_q, canon_q, a, m.get("category", "general"),
                          m.get("created_at", now), now))
                    imported_count += 1
                conn.commit()

            return True, imported_count, f"Successfully imported {imported_count} memories."
        except Exception as e:
            return False, 0, f"Import error: {str(e)}"
