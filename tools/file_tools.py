import os
import glob
from pathlib import Path
from typing import Optional

USER_HOME = Path.home()

# Common path aliases
KNOWN_FOLDERS = {
    "desktop": USER_HOME / "Desktop" if (USER_HOME / "Desktop").exists() else USER_HOME / "OneDrive" / "Desktop",
    "documents": USER_HOME / "OneDrive" / "Documents" if (USER_HOME / "OneDrive" / "Documents").exists() else USER_HOME / "Documents",
    "downloads": USER_HOME / "Downloads",
    "project": Path(__file__).resolve().parent.parent,
    "workspace": Path(__file__).resolve().parent.parent,
}

def resolve_path(path_str: str) -> Path:
    """Resolves aliases or relative paths into absolute paths."""
    clean_str = path_str.strip().strip("'\"")
    lower_str = clean_str.lower()

    # Check alias keywords
    for alias, alias_path in KNOWN_FOLDERS.items():
        if lower_str == alias:
            return alias_path
        if lower_str.startswith(alias + "\\") or lower_str.startswith(alias + "/"):
            remainder = clean_str[len(alias)+1:]
            return alias_path / remainder

    # Direct or relative path
    p = Path(clean_str)
    if not p.is_absolute():
        # Default relative to Documents or project
        if (KNOWN_FOLDERS["documents"] / clean_str).exists():
            return KNOWN_FOLDERS["documents"] / clean_str
        elif (KNOWN_FOLDERS["desktop"] / clean_str).exists():
            return KNOWN_FOLDERS["desktop"] / clean_str
        return KNOWN_FOLDERS["project"] / clean_str
    return p

def list_local_directory(folder_name_or_path: str = "documents") -> str:
    """
    Lists the files and folders inside a local directory on your PC.
    Use ONLY when the user explicitly asks to view, check, or list files in a folder.
    
    Args:
        folder_name_or_path: Name of folder or path (e.g. 'desktop', 'documents', 'downloads', 'project', or 'C:\\Users\\...')
    """
    try:
        target_dir = resolve_path(folder_name_or_path)
        if not target_dir.exists() or not target_dir.is_dir():
            return f"Directory '{target_dir}' does not exist or is not a folder."

        items = []
        entries = sorted(target_dir.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        
        # Limit to top 25 items for speech/display readability
        for item in entries[:25]:
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            else:
                size_kb = round(item.stat().st_size / 1024, 1)
                items.append(f"📄 {item.name} ({size_kb} KB)")

        if not items:
            return f"The folder '{target_dir.name}' is currently empty."

        total_count = len(list(target_dir.iterdir()))
        header = f"Contents of {target_dir} ({len(items)} of {total_count} items):\n"
        return header + "\n".join(items)

    except Exception as e:
        return f"Unable to list directory: {e}"

def read_local_file(file_path: str) -> str:
    """
    Reads the text contents of a local file on your PC.
    Use ONLY when the user explicitly asks to read, inspect, check, or summarize a local file.
    
    Args:
        file_path: Name of the file or path (e.g. 'notes.txt', 'desktop/todo.txt', 'report.md', or full path)
    """
    try:
        resolved = resolve_path(file_path)
        if not resolved.exists():
            # Search in Documents, Desktop, and Downloads
            for folder in [KNOWN_FOLDERS["documents"], KNOWN_FOLDERS["desktop"], KNOWN_FOLDERS["downloads"], KNOWN_FOLDERS["project"]]:
                candidate = folder / file_path
                if candidate.exists() and candidate.is_file():
                    resolved = candidate
                    break

        if not resolved.exists() or not resolved.is_file():
            return f"Could not find the file '{file_path}' on your system."

        # Read with multiple encoding fallbacks
        content = ""
        for enc in ["utf-8", "cp1252", "latin-1"]:
            try:
                with open(resolved, "r", encoding=enc) as f:
                    content = f.read(4000)  # Read up to 4KB of text
                break
            except Exception:
                continue

        if not content:
            return f"The file '{resolved.name}' is empty."

        truncated = content + ("\n... [Content truncated for length]" if len(content) >= 4000 else "")
        clean_text = truncated.encode("ascii", "ignore").decode("ascii")
        return f"Contents of '{resolved.name}':\n{clean_text}"

    except Exception as e:
        return f"Error reading file '{file_path}': {e}"

def search_local_files(query: str, search_in: str = "documents") -> str:
    """
    Searches for local files by filename or extension across your folders.
    Use ONLY when the user explicitly asks to find or search for a local file.
    
    Args:
        query: Filename, word, or extension to search (e.g. 'resume', 'budget', '*.py', '*.pdf')
        search_in: Folder to search in ('documents', 'desktop', 'downloads', 'project', or 'all')
    """
    try:
        folders_to_search = []
        if search_in.lower() == "all":
            folders_to_search = [KNOWN_FOLDERS["documents"], KNOWN_FOLDERS["desktop"], KNOWN_FOLDERS["downloads"], KNOWN_FOLDERS["project"]]
        else:
            folders_to_search = [resolve_path(search_in)]

        found_files = []
        pattern = f"*{query}*" if not query.startswith("*") else query

        for folder in folders_to_search:
            if not folder.exists():
                continue
            # Search top 2 levels
            for match in folder.glob(pattern):
                if not match.name.startswith(".") and match.name != "__pycache__":
                    found_files.append(f"{match.name} -> {match}")
            for match in folder.glob(f"*/*{pattern}"):
                if not match.name.startswith(".") and match.name != "__pycache__":
                    found_files.append(f"{match.name} -> {match}")

        if not found_files:
            return f"No local files matching '{query}' were found in {search_in}."

        unique_found = list(dict.fromkeys(found_files))[:15]
        return f"Found {len(unique_found)} file(s) matching '{query}':\n" + "\n".join(unique_found)

    except Exception as e:
        return f"Search error: {e}"

def write_local_file(file_path: str, content: str) -> str:
    """
    Creates or writes text content to a local file on your PC.
    Use ONLY when the user explicitly instructs to write, save, or create a file.
    
    Args:
        file_path: Destination file name or path (e.g. 'desktop/todo.txt', 'notes.md')
        content: The text content to write into the file
    """
    try:
        resolved = resolve_path(file_path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully saved file to '{resolved}'."
    except Exception as e:
        return f"Failed to write file: {e}"
