import os
import re
from pathlib import Path
from typing import List, Tuple, Optional
from core.safety import SafetyManager

safety = SafetyManager()

APPROVED_SEARCH_DIRS = {
    "downloads": Path.home() / "Downloads",
    "download": Path.home() / "Downloads",
    "desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "document": Path.home() / "Documents",
    "pictures": Path.home() / "Pictures",
    "picture": Path.home() / "Pictures",
    "photos": Path.home() / "Pictures",
    "photo": Path.home() / "Pictures",
    "screenshots": Path.home() / "Pictures" / "Screenshots"
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
PDF_EXTENSIONS = {".pdf"}

def resolve_whatsapp_file(
    file_query: str,
    folder_hint: Optional[str] = None,
    file_type: str = "pdf"
) -> Tuple[bool, str, List[Path]]:
    """
    Searches approved folders (Downloads, Desktop, Documents, Pictures) for the requested file.
    Ensures safe access, verifies readability, and detects multiple matching files.
    Returns (success, message_or_status, matching_paths_list).
    """
    raw_lower = file_query.strip().lower()
    clean_query = raw_lower
    # Remove generic keywords like 'ye', 'is', 'wali', 'se', 'folder', 'meri', 'ka', 'ki', 'file', 'photo', 'image', 'tasveer'
    clean_query = re.sub(r'\b(ye|yeh|this|is|wali|se|folder|meri|ka|ki|file|photo|image|tasveer)\b', '', clean_query).strip()

    # Determine folders to search
    folders_to_search: List[Path] = []
    if folder_hint and folder_hint.lower() in APPROVED_SEARCH_DIRS:
        target_dir = APPROVED_SEARCH_DIRS[folder_hint.lower()]
        if target_dir.exists():
            folders_to_search.append(target_dir)

    if not folders_to_search:
        # Default prioritized order: Downloads -> Desktop -> Documents -> Pictures
        for key in ["downloads", "desktop", "documents", "pictures", "screenshots"]:
            p = APPROVED_SEARCH_DIRS[key]
            if p.exists() and p not in folders_to_search:
                folders_to_search.append(p)

    target_extensions = PDF_EXTENSIONS if file_type == "pdf" else IMAGE_EXTENSIONS

    matched_files: List[Path] = []
    query_base = clean_query.replace(".pdf", "").replace(".png", "").replace(".jpg", "").replace(".jpeg", "").replace(".webp", "").strip(" _-")

    # If query is asking for latest/recent file, screenshot, or generic photo/doc without specific custom name
    is_latest_query = (
        any(w in raw_lower for w in ["latest", "screenshot", "photo", "pic", "image", "tasveer", "document.pdf", "latest.pdf", "latest_image"])
        or len(query_base) == 0
        or query_base in ["latest", "photo", "image", "doc", "document", "screenshot"]
    )

    for folder in folders_to_search:
        if not safety.is_path_safe(str(folder)):
            continue
        try:
            # Check files directly in folder and 1 level of subdirectories
            for item in folder.iterdir():
                if item.is_file() and item.suffix.lower() in target_extensions:
                    if is_latest_query:
                        matched_files.append(item)
                    elif query_base and query_base in item.name.lower():
                        matched_files.append(item)
                    elif clean_query and clean_query in item.name.lower():
                        matched_files.append(item)
        except Exception:
            continue

    if is_latest_query and matched_files:
        # Sort by modification time descending to pick the most recent file
        matched_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        latest = matched_files[0]
        return True, f"Found most recent file: {latest.name}", [latest]

    if not matched_files:
        # Try finding any file with exact extension if user specified e.g. 'assignment.pdf'
        for folder in folders_to_search:
            for item in folder.glob("*.*"):
                if item.is_file() and item.suffix.lower() in target_extensions:
                    if query_base and any(word in item.name.lower() for word in query_base.split() if len(word) > 2):
                        matched_files.append(item)

    # Filter readable files
    valid_files = [f for f in matched_files if f.exists() and os.access(str(f), os.R_OK)]
    # De-duplicate by resolved path
    seen = set()
    unique_files = []
    for f in valid_files:
        res = str(f.resolve()).lower()
        if res not in seen:
            seen.add(res)
            unique_files.append(f)

    if not unique_files:
        searched_names = ", ".join([f.name for f in folders_to_search[:3]])
        return False, f"Boss, '{file_query}' approved folders ({searched_names}) mein nahi mila.", []

    if len(unique_files) == 1:
        chosen = unique_files[0]
        return True, f"File found: {chosen.name}", [chosen]

    # Multiple files matched!
    # Check if there is an exact filename match
    exact = [f for f in unique_files if f.name.lower() == file_query.lower() or f.name.lower() == f"{clean_query}.{file_type}"]
    if len(exact) == 1:
        return True, f"File found: {exact[0].name}", [exact[0]]

    return False, "MULTIPLE_FILES", unique_files[:5]
