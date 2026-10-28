import os
import re
import subprocess
from pathlib import Path
from core.safety import SafetyManager

safety = SafetyManager()

KNOWN_FOLDERS = {
    "downloads": Path.home() / "Downloads",
    "download": Path.home() / "Downloads",
    "desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "document": Path.home() / "Documents",
    "pictures": Path.home() / "Pictures",
    "picture": Path.home() / "Pictures",
    "photos": Path.home() / "Pictures",
    "photo": Path.home() / "Pictures",
    "videos": Path.home() / "Videos",
    "video": Path.home() / "Videos",
    "music": Path.home() / "Music",
    "c drive": Path("C:\\"),
    "d drive": Path("D:\\")
}

EXT_CATEGORIES = {
    "pdf": [".pdf"],
    "image": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".ico", ".svg"],
    "photo": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".ico", ".svg"],
    "pic": [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".ico", ".svg"],
    "video": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv"],
    "audio": [".mp3", ".wav", ".m4a", ".aac", ".ogg"],
    "song": [".mp3", ".wav", ".m4a", ".aac", ".ogg"],
    "word": [".docx", ".doc"],
    "doc": [".docx", ".doc", ".pdf", ".txt"],
    "document": [".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx", ".csv"],
    "excel": [".xlsx", ".xls", ".csv"],
    "sheet": [".xlsx", ".xls", ".csv", ".pdf"],
    "ppt": [".pptx", ".ppt"],
    "text": [".txt", ".md", ".log"],
    "code": [".py", ".js", ".html", ".css", ".json", ".cpp", ".java", ".c"]
}

def create_folder(folder_name: str, base_directory: str = None) -> tuple[bool, str]:
    if not base_directory:
        base_directory = str(Path.home() / "Documents" / "JarvisProjects")
    
    target_dir = Path(base_directory) / folder_name
    if not safety.is_path_safe(str(target_dir)):
        return False, f"Access denied: Path '{target_dir}' is outside approved directories."

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        return True, f"Folder '{folder_name}' created at {target_dir}."
    except Exception as e:
        return False, f"Failed to create folder: {str(e)}"

def save_note(title: str, content: str, notes_dir: str = None) -> tuple[bool, str]:
    if not notes_dir:
        notes_dir = str(Path.home() / "Documents" / "JarvisNotes")

    target_file = Path(notes_dir) / f"{title}.txt"
    if not safety.is_path_safe(str(target_file)):
        return False, "Access denied: Target directory is not approved."

    try:
        Path(notes_dir).mkdir(parents=True, exist_ok=True)
        with open(target_file, "a", encoding="utf-8") as f:
            f.write(f"\n--- Note saved on {Path(__file__).name} ---\n{content}\n")
        return True, f"Note '{title}' saved successfully."
    except Exception as e:
        return False, f"Failed to save note: {str(e)}"

def search_files(query: str, search_root: str = None) -> tuple[bool, list[str]]:
    if not search_root:
        search_root = str(Path.home() / "Documents")

    if not safety.is_path_safe(search_root):
        return False, []

    matches = []
    try:
        for root, dirs, files in os.walk(search_root):
            for file in files:
                if query.lower() in file.lower():
                    matches.append(str(Path(root) / file))
                    if len(matches) >= 10:
                        break
            if len(matches) >= 10:
                break
        return True, matches
    except Exception:
        return False, []

def open_file_or_folder(path_str: str) -> tuple[bool, str]:
    target = Path(path_str).resolve()
    if not safety.is_path_safe(str(target)):
        return False, "Access denied: Path is outside approved directories."

    if not target.exists():
        return False, f"Path '{path_str}' does not exist."

    try:
        os.startfile(str(target))
        return True, f"Opened {target.name}."
    except Exception as e:
        # Fallback for images or blocked file associations: open File Explorer with item highlighted
        try:
            import subprocess
            subprocess.Popen(f'explorer.exe /select,"{target}"', shell=True)
            return True, f"Opened File Explorer showing {target.name}."
        except Exception as inner_e:
            return False, f"Failed to open: {str(e)}"

def search_file_everywhere(query: str, preferred_exts: list[str] = None, limit: int = 20) -> list[str]:
    """Fast indexed scan across user's laptop spaces."""
    query_clean = query.lower().strip()
    category_words = {"pdf", "image", "photo", "pic", "tasveer", "video", "audio", "song", "music", "doc", "document", "sheet", "excel", "ppt", "file", "folder"}
    raw_tokens = [t for t in re.split(r'[\s_\-\.]+', query_clean) if len(t) >= 2]
    meaningful_tokens = [t for t in raw_tokens if t not in category_words]
    if not meaningful_tokens and raw_tokens:
        meaningful_tokens = raw_tokens

    search_roots = [
        Path.home() / "Downloads",
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Pictures",
        Path.home() / "Videos",
        Path.home() / "Music",
        Path.home()
    ]
    
    # Check other drives
    for drive_letter in ["D:\\", "E:\\"]:
        d = Path(drive_letter)
        if d.exists():
            search_roots.append(d)

    candidates = []
    seen = set()
    skip_dirs = {"appdata", "node_modules", ".git", ".gemini", "__pycache__", "windows", "program files", "program files (x86)", "$recycle.bin"}

    for s_root in search_roots:
        if not s_root.exists():
            continue
        try:
            for root, dirs, files in os.walk(str(s_root)):
                # Prune noisy / system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in skip_dirs]

                for f in files:
                    full_p = os.path.join(root, f)
                    if full_p in seen:
                        continue

                    fl = f.lower()
                    ext = os.path.splitext(fl)[1]

                    # Token match calculation
                    matched_count = sum(1 for t in meaningful_tokens if t in fl or (len(t) > 3 and t[:4] in fl))
                    score = 0
                    
                    if query_clean and query_clean in fl:
                        score += 100
                    if meaningful_tokens and matched_count == len(meaningful_tokens):
                        score += 80
                    elif matched_count > 0:
                        score += matched_count * 25

                    if preferred_exts and ext in preferred_exts:
                        score += 15

                    # Only accept if at least one meaningful token matched or query was empty
                    if score > 0 and (matched_count > 0 or not meaningful_tokens):
                        try:
                            mtime = os.path.getmtime(full_p)
                        except Exception:
                            mtime = 0
                        candidates.append((score, mtime, full_p))
                        seen.add(full_p)

                # Limit depth for speed
                depth = root.count(os.sep) - str(s_root).count(os.sep)
                if depth >= 4:
                    dirs.clear()
        except Exception:
            pass

    # Sort candidates by score DESC, then by mtime DESC (newest first)
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [c[2] for c in candidates[:limit]]

def open_in_file_explorer(path_str: str) -> tuple[bool, str]:
    """Launch File Explorer and highlight/select target file or open folder."""
    target = Path(path_str).resolve()
    if not target.exists():
        return False, f"File or folder '{path_str}' nahi mili."
    
    try:
        if target.is_dir():
            subprocess.Popen(f'explorer.exe "{target}"', shell=True)
            return True, f"File Explorer mein '{target.name}' folder open kar diya hai."
        else:
            subprocess.Popen(f'explorer.exe /select,"{target}"', shell=True)
            return True, f"File Explorer mein '{target.name}' select karke open kar diya hai."
    except Exception as e:
        return False, f"File Explorer open karne mein error: {str(e)}"

def smart_open_file_or_folder(raw_query: str) -> tuple[bool, str, str]:
    """
    Search and open any file or folder across the laptop.
    Supports opening in default app or selecting in File Explorer.
    """
    text_lower = raw_query.lower()
    in_explorer = any(w in text_lower for w in ["file explorer", "explorer", "folder mein", "folder me", "location", "dikhao", "select karo"])

    # 1. Check if user wants to open a standard known folder
    for folder_name, folder_path in KNOWN_FOLDERS.items():
        pattern = rf'\b{re.escape(folder_name)}\s+folder\b|\bfolder\s+{re.escape(folder_name)}\b'
        is_exact_folder_cmd = bool(re.search(pattern, text_lower)) or (
            folder_name in text_lower and len(text_lower.split()) <= 4 and not any(ext in text_lower for ext in ["pdf", "jpg", "jpeg", "png", "sheet", "doc", "file", "mark", "pic", "image"])
        )
        if is_exact_folder_cmd and any(w in text_lower for w in ["folder", "kholo", "open", "chalao", "dikhao"]):
            if folder_path.exists():
                subprocess.Popen(f'explorer.exe "{folder_path}"', shell=True)
                return True, f"File Explorer mein '{folder_name.capitalize()}' folder open kar diya hai boss.", folder_name

    # 2. Detect requested file category extensions
    preferred_exts = None
    for cat_name, exts in EXT_CATEGORIES.items():
        if cat_name in text_lower:
            preferred_exts = exts
            break

    # 3. Clean search query
    clean = re.sub(
        r'file explorer me|file explorer mein|file explorer|explorer me|explorer mein|explorer|'
        r'kholo|open karo|open kar do|open|dikhao|show karo|show|batao|chalao|dhoondo|'
        r'laptop me|laptop mein|meri|mera|mere|koi|bhi|v|ek|wali|wala|wale|file|folder',
        ' ',
        text_lower
    )
    # Remove Hindi particles
    clean = re.sub(r'\b(ka|ki|ke|me|mein|se|ko|par|pe)\b', ' ', clean)
    clean = ' '.join(clean.split()).strip()

    if not clean and preferred_exts:
        clean = ""  # Will pick the newest file of this extension

    matches = search_file_everywhere(clean, preferred_exts=preferred_exts, limit=10)
    if not matches:
        return False, f"Boss, laptop mein '{clean or raw_query}' se milti-julti koi file nahi mili. Ek baar naam check kar lijiye.", ""

    chosen_file = matches[0]
    filename = Path(chosen_file).name

    if in_explorer:
        ok, msg = open_in_file_explorer(chosen_file)
        return ok, msg, filename
    else:
        try:
            os.startfile(chosen_file)
            return True, f"Boss, '{filename}' open kar di hai!", filename
        except Exception as e:
            # Fallback to file explorer
            ok, msg = open_in_file_explorer(chosen_file)
            return ok, f"Direct open nahi hua toh File Explorer mein '{filename}' select kar diya hai: {msg}", filename

