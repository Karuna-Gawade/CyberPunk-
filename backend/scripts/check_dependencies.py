"""
Dependency allow-list scanner.
Verifies that all Python runtime code imports ONLY approved foundational packages.
Ignores `samples/` (dev-only document generator).
"""

import ast
import os
import sys
from pathlib import Path

ALLOWED_TOP_LEVEL_MODULES = {
    # Standard library (built-in)
    "__future__", "abc", "argparse", "ast", "asyncio", "base64", "collections", "contextlib", "copy",
    "csv", "dataclasses", "datetime", "decimal", "difflib", "enum", "functools", "glob",
    "hashlib", "hmac", "html", "importlib", "inspect", "io", "itertools", "json",
    "logging", "math", "multiprocessing", "operator", "os", "pathlib", "pickle",
    "platform", "pprint", "random", "re", "shutil", "socket", "sqlite3", "stat", "string",
    "subprocess", "sys", "tempfile", "threading", "time", "traceback", "typing",
    "unittest", "urllib", "uuid", "warnings", "weakref", "zipfile", "zlib",
    
    # Approved foundational dependencies
    "fastapi",
    "pydantic",
    "pydantic_core",
    "uvicorn",
    "starlette",
    "fitz",         # PyMuPDF
    "pymupdf",
    "cv2",          # OpenCV
    "numpy",
    "reportlab",
    "pytest",
    
    # Internal project packages
    "backend",
    "app",
    "models",
    "api",
    "services",
    "db",
    "tests",
    "contracts",
}

FORBIDDEN_KEYWORDS = [
    "openai", "anthropic", "langchain", "llama", "transformers", "torch", "paddleocr",
    "easyocr", "pyaadhaar", "pyzbar", "rapidfuzz", "google.genai", "google_genai"
]


def extract_imports_from_file(file_path: Path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_pkg = alias.name.split(".")[0]
                imports.append((top_pkg, alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top_pkg = node.module.split(".")[0]
                imports.append((top_pkg, node.module, node.lineno))
    return imports


def check_directory(root_dir: Path):
    violations = []
    runtime_dirs = [root_dir / "backend" / "app", root_dir / "backend" / "tests"]

    for d in runtime_dirs:
        if not d.exists():
            continue
        for py_path in d.rglob("*.py"):
            imports = extract_imports_from_file(py_path)
            for top_pkg, full_name, lineno in imports:
                if top_pkg not in ALLOWED_TOP_LEVEL_MODULES:
                    violations.append(
                        f"Disallowed import '{full_name}' at {py_path}:{lineno}"
                    )
                for forbidden in FORBIDDEN_KEYWORDS:
                    if forbidden in full_name.lower():
                        violations.append(
                            f"Strictly forbidden AI/cloud package '{full_name}' at {py_path}:{lineno}"
                        )
    return violations


def main():
    root = Path(__file__).resolve().parent.parent.parent
    violations = check_directory(root)
    if violations:
        print("[FAIL] Dependency Allow-list Violations Detected:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)
    else:
        print("[PASS] All runtime imports conform strictly to Section 3.1 allow-list policy.")
        sys.exit(0)


if __name__ == "__main__":
    main()
