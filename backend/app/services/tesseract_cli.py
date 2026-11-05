"""
Tesseract CLI helper for OCR execution, version checking, and language discovery.
Uses subprocess to call Tesseract directly (no wrapper libraries).
Handles missing Tesseract gracefully with explicit "OCR engine unavailable" states.
"""

import os
import shutil
import subprocess
from typing import List, Optional, Tuple


def find_tesseract_binary() -> Optional[str]:
    """Finds tesseract binary in PATH or standard system installation directories."""
    # First check PATH
    binary = shutil.which("tesseract")
    if binary:
        return binary

    # Common Windows installation directories
    candidate_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expanduser(r"~\tesseract\tesseract.exe"),
    ]
    for path in candidate_paths:
        if os.path.isfile(path):
            return path

    return None


def get_tesseract_info() -> Tuple[bool, Optional[str], List[str]]:
    """
    Checks if Tesseract CLI is available and retrieves version and installed language packs.
    Returns: (is_available, version_string, list_of_languages)
    """
    binary = find_tesseract_binary()
    if not binary:
        return False, None, []

    version = None
    languages: List[str] = []

    # Get version
    try:
        proc_ver = subprocess.run(
            [binary, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        if proc_ver.returncode == 0 or proc_ver.stdout:
            # First line e.g. "tesseract 5.4.0..."
            first_line = (proc_ver.stdout or proc_ver.stderr).splitlines()
            if first_line:
                version = first_line[0].strip()
    except Exception:
        pass

    # Get installed languages
    try:
        proc_langs = subprocess.run(
            [binary, "--list-langs"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
        )
        output = proc_langs.stdout or proc_langs.stderr
        lines = [line.strip() for line in output.splitlines()]
        # Typically begins with header "List of available languages (X):"
        languages = [l for l in lines if l and not l.lower().startswith("list of")]
    except Exception:
        pass

    return True, version, languages
