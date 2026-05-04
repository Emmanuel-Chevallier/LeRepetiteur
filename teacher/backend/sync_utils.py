import hashlib
from pathlib import Path
import os
from typing import Dict

def calculate_file_hash(file_path: Path) -> str:
    """Calculates info-hash (MD5) of a file."""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return ""

def generate_manifest(root_dir: Path) -> Dict[str, str]:
    """
    Scans a directory recursively and returns a dict:
    { "relative/path/to/file": "hash_string" }
    """
    manifest = {}
    for root, dirs, files in os.walk(root_dir):
        # Exclude temp directories
        if "temp" in dirs:
            dirs.remove("temp")
            
        for file in files:
            file_path = Path(root) / file
            rel_path = file_path.relative_to(root_dir).as_posix()
            manifest[rel_path] = calculate_file_hash(file_path)
            
    return manifest
