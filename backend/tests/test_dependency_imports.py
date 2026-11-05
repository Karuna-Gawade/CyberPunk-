"""
Runtime Dependency Import and Allow-List Verifier.
Spec Requirement:
- Ensure no forbidden AI/LLM/Cloud dependencies are imported or loaded at runtime.
- Allow-list strictly enforced across all backend modules.
"""

import sys
import importlib
import pytest

FORBIDDEN_PACKAGES = [
    "openai",
    "anthropic",
    "langchain",
    "llama_index",
    "google.generativeai",
    "transformers",
    "torch",
    "tensorflow",
    "paddleocr",
    "easyocr",
    "pytesseract",  # Only CLI subprocess is permitted, no wrappers
    "rapidfuzz",
    "pyaadhaar",
    "pyzbar",
]

BACKEND_MODULES_TO_CHECK = [
    "backend.app.main",
    "backend.app.models.contracts",
    "backend.app.db.storage",
    "backend.app.services.audit",
    "backend.app.services.classification",
    "backend.app.services.ingestion",
    "backend.app.services.render",
    "backend.app.services.pii",
    "backend.app.services.tesseract_cli",
    "backend.app.services.injection",
    "backend.app.services.escalation",
    "backend.app.services.explanation",
    "backend.app.services.dossier",
    "backend.app.services.extraction.text_layer",
    "backend.app.services.extraction.tesseract_ocr",
    "backend.app.services.extraction.aadhaar_qr",
    "backend.app.services.extraction.field_parser",
    "backend.app.services.rules.verhoeff",
    "backend.app.services.rules.pan",
    "backend.app.services.rules.salary",
    "backend.app.services.rules.bank",
    "backend.app.services.rules.aadhaar_qr_match",
    "backend.app.services.rules.within_doc",
    "backend.app.services.rules.rules_runner",
    "backend.app.services.correlation.name_match",
    "backend.app.services.correlation.dates",
    "backend.app.services.correlation.cross_doc",
    "backend.app.services.forensics.pdf_native",
    "backend.app.services.forensics.image_forensics",
]


def test_no_forbidden_packages_imported():
    """Verify that importing all backend components never pulls in any forbidden packages."""
    for mod_name in BACKEND_MODULES_TO_CHECK:
        importlib.import_module(mod_name)

    loaded_modules = set(sys.modules.keys())

    for forbidden in FORBIDDEN_PACKAGES:
        # Check if forbidden package or any submodule is loaded
        violating = [m for m in loaded_modules if m == forbidden or m.startswith(f"{forbidden}.")]
        assert len(violating) == 0, f"Violation: Forbidden package '{forbidden}' was imported into runtime! (Loaded: {violating})"
