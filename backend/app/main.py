"""
Main FastAPI Application for PS-2 AI Document Forensics System.
Advisory output. Final decision rests with the human reviewer.
"""

from dotenv import load_dotenv

# Load optional .env variables (e.g. GEMINI_API_KEY, GROQ_API_KEY)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.models.contracts import CapabilitiesReport, CapabilityStatus
from backend.app.services.tesseract_cli import get_tesseract_info
from backend.app.api.investigations import router as investigations_router

app = FastAPI(
    title="AI Document Forensics and Contextual Intelligence System",
    description="Advisory forensic and contextual intelligence engine for Indian financial & ID documents.",
    version="1.0.0",
)

# Enable CORS for local Vite development frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(investigations_router)
app.include_router(investigations_router, prefix="/api")


@app.get("/health")
@app.get("/api/health")
def health_check():
    is_available, version, _ = get_tesseract_info()
    return {
        "status": "healthy",
        "advisory": "Advisory output. Final decision rests with the human reviewer.",
        "tesseract_detected": is_available,
        "tesseract_version": version,
    }


@app.get("/capabilities", response_model=CapabilitiesReport)
@app.get("/api/capabilities", response_model=CapabilitiesReport)
def get_capabilities() -> CapabilitiesReport:
    is_available, version, languages = get_tesseract_info()

    capabilities = [
        CapabilityStatus(
            feature="Document Classification",
            status="implemented",
            detail="Two-stage classifier: TF-IDF + XGBoost ML engine with heuristic + regex fallback for Aadhaar, PAN, Salary Slip, Bank Statement, Loan Application, Form 15G, Payment Instruction.",
        ),
        CapabilityStatus(
            feature="XGBoost ML Document Classifier",
            status="implemented",
            detail="Offline-trained supervised gradient boosted decision trees over n-gram TF-IDF vectors; automatic cold-start fallback.",
        ),
        CapabilityStatus(
            feature="Multi-Format Ingestion",
            status="implemented",
            detail="Full pipeline support for PDF, DOCX, XLSX, PNG, JPG, JPEG, TIFF, BMP, and WebP with 150 DPI rendering.",
        ),
        CapabilityStatus(
            feature="Signature Presence & Alignment Forensics",
            status="implemented",
            detail="Visual stroke density verification in execution zones and span baseline displacement analysis.",
        ),
        CapabilityStatus(
            feature="PDF Text-Layer Extraction",
            status="implemented",
            detail="Direct extraction of vector text, spans, fonts, and colors via PyMuPDF.",
        ),
        CapabilityStatus(
            feature="Tesseract OCR CLI",
            status="implemented" if is_available else "unsupported",
            detail=f"Word boxes + confidences at 300 DPI scaled to 150 DPI. Status: {'Ready (' + (version or '') + ')' if is_available else 'OCR engine unavailable'}",
        ),
        CapabilityStatus(
            feature="Aadhaar Secure QR Extraction",
            status="implemented",
            detail="OpenCV QR detection + custom zlib decompression + big-integer demographic decoding.",
        ),
        CapabilityStatus(
            feature="UIDAI Cryptographic PKI Signature Verification",
            status="unsupported",
            detail="Unsupported by design in offline mode: requires live UIDAI certificate revocation checks and government root keys.",
        ),
        CapabilityStatus(
            feature="Deterministic Rules (D1)",
            status="implemented",
            detail="Verhoeff, PAN structure, salary arithmetic, bank running balance continuity.",
        ),
        CapabilityStatus(
            feature="PDF-Native Forensics (D2)",
            status="implemented",
            detail="Producer/Creator analysis, multiple %%EOF markers, sibling font inconsistency, text-layer vs OCR diff.",
        ),
        CapabilityStatus(
            feature="In-House Name Matching (D8)",
            status="implemented",
            detail="Pure Python Jaro-Winkler + Levenshtein + token set permutations + Indian honorifics and initials normalization.",
        ),
        CapabilityStatus(
            feature="Prompt-Injection Defense (D5)",
            status="implemented",
            detail="Scanning visible and hidden text spans for adversarial instruction patterns.",
        ),
        CapabilityStatus(
            feature="Error Level Analysis (ELA)",
            status="partial",
            detail="Local OpenCV re-compression difference. Weak supporting signal.",
        ),
        CapabilityStatus(
            feature="Hash-Chained Audit Trail (D4)",
            status="implemented",
            detail="Append-only event ledger with SHA-256 chain verification.",
        ),
        CapabilityStatus(
            feature="Human Case Decision Workflow (D6)",
            status="implemented",
            detail="Advisory tool output; enforces human decision before dossier finalization.",
        ),
        CapabilityStatus(
            feature="PII Masking & Logged Reveal (D7)",
            status="implemented",
            detail="Default masking for Aadhaar and PAN with audited reveal action.",
        ),
        CapabilityStatus(
            feature="LLM / Generative AI Reasoning",
            status="unsupported",
            detail="Unsupported by design: System uses 100% deterministic rules and template engines for offline, explainable forensics.",
        ),
    ]

    return CapabilitiesReport(
        tesseract_available=is_available,
        tesseract_version=version,
        tesseract_languages=languages,
        system_mode="offline",
        capabilities=capabilities,
    )
