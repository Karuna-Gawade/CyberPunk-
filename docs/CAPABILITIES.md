# Capabilities & System Support Matrix

This document provides a transparent accounting of all system capabilities, explicitly categorizing features as **Implemented**, **Partial**, **Planned**, or **Unsupported**.

| Feature / Subsystem | Status | Description & Limitations |
|---|---|---|
| **Document Classification** | Implemented | Heuristic + regex + layout classification for Aadhaar, PAN, Salary Slip, Bank Statement. Unsupported types fail gracefully to manual review. |
| **PDF Text-Layer Extraction** | Implemented | Direct extraction of vector text, spans, fonts, sizes, and colors via PyMuPDF. |
| **Tesseract OCR (CLI)** | Implemented | Local CLI invocation (`subprocess`), TSV output parsing, word bounding boxes, normalized word confidence. Operates at 300 DPI, scaled to 150 DPI. |
| **Aadhaar Secure QR Extraction** | Implemented | OpenCV QR detection + custom zlib decompression + big-integer demographic decoding. |
| **Aadhaar UIDAI PKI Signature Verification** | Unsupported | Unsupported by design in offline mode: requires live UIDAI certificate revocation checks and government root keys. |
| **Verhoeff Checksum (Aadhaar)** | Implemented | Pure Python implementation of Dihedral $D_5$ group multiplication and permutation tables. |
| **PAN Format & Holder Validation** | Implemented | Regex structure validation (`^[A-Z]{5}[0-9]{4}[A-Z]$`), 4th character holder-type decoding, 5th character surname initial match. |
| **Payroll Arithmetic Audit** | Implemented | Component sum to Gross, Gross minus Deductions to Net Pay. PF basic wage check reported as Observation. |
| **Bank Balance Continuity Engine** | Implemented | Row-by-row transaction continuity checking; identifies the exact first broken row index. |
| **Cross-Document Field Correlation** | Implemented | Two-sided comparison of Name, DOB, PAN, and Salary Credits vs Slip Net Pay with two-sided evidence bounding boxes. |
| **In-House Name Matching** | Implemented | Pure Python Jaro-Winkler + Levenshtein + token set permutations + Indian honorifics and initials normalization. Zero external libraries. |
| **PDF-Native Metadata Forensics** | Implemented | Producer/Creator analysis, editing software detection, creation vs. modification date discrepancies. |
| **PDF Incremental Re-save Forensics** | Implemented | Detection and counting of multiple `%%EOF` markers. |
| **PDF Sibling Font Inconsistency** | Implemented | Detection of font name, size, or weight deviations within table rows/columns. |
| **Text-Layer vs OCR Diff Detection** | Implemented | Comparison between vector text stream and rasterized OCR text for overlaid tamper detection. |
| **Prompt-Injection Defense** | Implemented | Scanning visible and hidden text spans for adversarial instruction patterns; isolated so adversarial text cannot alter scoring. |
| **Error Level Analysis (ELA)** | Partial | Local OpenCV re-compression difference. Marked as weak supporting signal due to JPEG false-positive rates on multi-save files. |
| **Copy-Move Image Detection** | Partial | Block-based DCT / keypoint patch comparison. Marked as weak supporting signal. |
| **Hash-Chained Audit Trail** | Implemented | Append-only SQLite event ledger with SHA-256 chain verification. |
| **Human Review & Decision Engine** | Implemented | Per-finding review actions (Confirm/Dismiss/Escalate) and Case Decision workflow (`rely_on_tool_output`, `partially_rely`, `disregard_tool_output`, `needs_more_information`). |
| **PII Redaction & Audited Reveal** | Implemented | Masked display of Aadhaar (`XXXX XXXX 1234`) and PAN; unmasking audited with user identity and timestamp. |
| **Investigative Dossier PDF Export** | Implemented | Comprehensive PDF dossier generated via ReportLab with cropped evidence thumbnails, DRAFT watermark, and findings breakdown. |
| **LLM / Generative AI Reasoning** | Unsupported | **Unsupported by design**: System uses 100% deterministic rules, forensic algorithms, and template engines to ensure air-gapped, explainable forensics. |
| **Cloud / SaaS API Integrations** | Unsupported | **Unsupported by design**: System operates fully offline with zero telemetry or outbound network calls. |
