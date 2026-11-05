# System Architecture

## Overview
The AI Document Forensics and Contextual Intelligence System is an offline, deterministic, evidence-linked verification pipeline designed for high-assurance forensic investigation of Indian identity and financial document bundles (Aadhaar, PAN, Salary Slips, Bank Statements).

```mermaid
flowchart TD
    subgraph Client["Frontend (React + Vite + TypeScript)"]
        UI_Upload["Upload & Bundle View"]
        UI_Doc["Document View (Overlay 150 DPI)"]
        UI_Cross["Cross-Document Matrix"]
        UI_Review["Findings & Human Review Screen"]
        UI_Decision["Case Decision Workflow"]
        UI_Dossier["Dossier & Audit Explorer"]
    end

    subgraph API["FastAPI Backend (Python 3.11+)"]
        Endpoint_Ingest["Ingestion & SHA-256 Storage"]
        Endpoint_Classify["Classification Service"]
        Endpoint_Extract["Extraction Engine (Text Layer + OCR + QR)"]
        Endpoint_Forensics["Forensics Engine (PDF-Native + CV)"]
        Endpoint_Rules["Deterministic Rules Engine"]
        Endpoint_Correlation["Cross-Doc Correlation & Fuzzy Match"]
        Endpoint_Escalate["Tiering & Review Priority Scoring"]
        Endpoint_Templates["Deterministic Explanation Engine"]
        Endpoint_Audit["Append-Only Hash-Chained Audit Ledger"]
        Endpoint_Dossier["ReportLab Dossier PDF Generator"]
    end

    subgraph Engines["Engines & Storage"]
        Tesseract_CLI["Tesseract OCR CLI (300 DPI -> 150 DPI)"]
        PyMuPDF["PyMuPDF (Text Layer, Fonts, Render 150 DPI)"]
        OpenCV["OpenCV (ELA, QR Detection, Noise)"]
        SQLite[("SQLite Append-Only DB")]
        Disk[("Read-Only Storage (Artifacts/Thumbnails)")]
    end

    UI_Upload --> Endpoint_Ingest
    Endpoint_Ingest --> Disk
    Endpoint_Ingest --> Endpoint_Classify
    Endpoint_Classify --> Endpoint_Extract
    Endpoint_Extract --> PyMuPDF
    Endpoint_Extract --> Tesseract_CLI
    Endpoint_Extract --> OpenCV
    Endpoint_Extract --> Endpoint_Forensics
    Endpoint_Forensics --> Endpoint_Rules
    Endpoint_Rules --> Endpoint_Correlation
    Endpoint_Correlation --> Endpoint_Escalate
    Endpoint_Escalate --> Endpoint_Templates
    Endpoint_Templates --> SQLite
    Endpoint_Ingest --> Endpoint_Audit
    Endpoint_Audit --> SQLite

    UI_Doc <--> Endpoint_Extract
    UI_Cross <--> Endpoint_Correlation
    UI_Review <--> Endpoint_Escalate
    UI_Decision <--> Endpoint_Audit
    UI_Dossier <--> Endpoint_Dossier
```

## Core Architectural Modules

1. **Ingestion & Integrity**: Calculates cryptographic SHA-256 on ingest, stores pristine files as read-only, logs immutable audit entry.
2. **Classification**: Layout and keyword heuristic classifier categorizing documents into Aadhaar, PAN, Salary Slip, Bank Statement, or gracefully falling back to Unsupported.
3. **Extraction & Normalization**:
   - Vector PDFs extracted via PyMuPDF (source: `text_layer`).
   - Scanned pages rasterized to 300 DPI and processed via Tesseract CLI (source: `ocr`), with bounding boxes normalized to standard 150 DPI render space.
   - Aadhaar Secure QR codes decoded via OpenCV and pure Python zlib/big-integer unpacking (source: `qr`).
4. **Deterministic Validation Rules**: Pure functional checks (Verhoeff, PAN structure, salary arithmetic, bank running balance continuity, date plausibility).
5. **Cross-Document Correlation**: Multi-document matching on shared entities (Name, DOB, PAN, Salary Credit vs Net Pay) utilizing an in-house Indian phonetic and token-permutation matcher.
6. **PDF-Native Forensics**: PyMuPDF span-level font/size inspection, incremental `%%EOF` re-save counters, metadata editing-software detection, and vector text vs OCR overlay diffing.
7. **Adversarial Instruction Defense**: Proactive scanning for prompt-injection patterns in visible and hidden layers, isolating adversarial strings from scoring.
8. **Three-Tier Escalation & Review Priority**: Strict classification into `Observation`, `Inconsistency`, and `Potential manipulation` (requiring $\ge 2$ independent signal types). Review priority calculated from a transparent points table.
9. **Deterministic Explanation Generator**: Parameterized string templates strictly bound to extracted field evidence; zero hallucination, zero prohibited terms.
10. **Human Review & Decision Core**: Enforces advisory operation. Dossiers are watermarked `DRAFT` until a human reviewer records a binding Case Decision.
11. **Cryptographic Audit Ledger**: Sequential SHA-256 hash chaining of canonical JSON records to detect retrospective database tampering.
