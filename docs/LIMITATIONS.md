# System Limitations & Boundary Conditions

In alignment with forensic reporting standards (ISO/IEC 27037, 27041, 27042, NIST SP 800-86), this document outlines the operational boundaries, known limitations, and non-supported capabilities of the AI Document Forensics System.

## 1. Signature Analysis Boundaries
- **Visual Presence & Execution Check:** The system verifies the physical presence of ink stroke pixels in dedicated signature boxes and detects spatial overlap with extracted form fields (`signature_region_empty`, `signature_placement_overlap`).
- **Biometric Signature Comparison (Unsupported):** The system **does not perform biometric signature matching**, dynamic pen-pressure analysis, stroke order verification, or forensic graphology across documents. Signatures are verified for execution state and layout boundaries only.

## 2. Handwriting & Multilingual OCR
- **Handwritten Documents (Unsupported):** The ingestion pipeline and OCR engine are engineered specifically for machine-printed typography and structured form documents. Free-form handwritten notes, handwritten endorsements, and cursive text are unsupported.
- **Multilingual OCR:** The system operates on English-language printed text and bilingual Indian identity headers. Regional vernacular scripts without Roman transliteration are flagged as manual review candidates.

## 3. General Deep Vision Layout Models
- **Deterministic vs Deep Vision Models:** The system utilizes coordinate geometry, spatial bounding box math, and supervised XGBoost ML over TF-IDF n-grams rather than heavy multimodal deep learning layout transformers (such as LayoutLMv3 or Donut). This design choice ensures 100% offline air-gapped execution, low latency (< 1.5 seconds per bundle), and deterministic, auditable decisions.

## 4. Cryptographic Signature Verification
- **UIDAI Aadhaar Digital Signature:** The system extracts and decodes the demographic payload from the Aadhaar Secure QR code (zlib-compressed big-integer format), but **does not verify the cryptographic X.509 UIDAI PKI signature**. Offline systems without live certificate revocation lists (CRL) cannot guarantee public-key validity without government root keys.
- **Bank Statement Digital Signatures:** PDF digital signatures (DocuSign, Adobe Sign, etc.) are verified for metadata anomalies and revisions (`%%EOF`), but cryptographic trust chain validation against external trust lists is out of scope for offline operation.

## 5. Image Forensics as Weak Supporting Signals
- **Error Level Analysis (ELA):** ELA detects compression differences across JPEG blocks. However, normal multiple saves, WhatsApp/messaging re-compression, and scanner downsampling naturally cause high ELA variations. ELA is treated strictly as a **weak supporting signal** and can never alone escalate an issue beyond an **Observation**.
- **Copy-Move & Noise Inconsistency:** Heavy blurring or aggressive scanner binarization can mask copy-move artifacts or create false block matches.

## 6. Office Document Ingestion
- **DOCX and XLSX Conversion:** Office files (.docx and .xlsx) are parsed natively for text and rendered server-side to 150 DPI pages using ReportLab and PyMuPDF. Complex proprietary Visual Basic macros, external linked worksheets, and embedded OLE objects are ignored for security.

## 7. OCR Engine Accuracy & Physical Scans
- **Tesseract Limitations:** Tesseract 5.x performance depends on document resolution, deskew quality, and contrast. On low-resolution scans (<150 DPI) or degraded physical documents, character confusion (e.g., `0` vs `O`, `1` vs `l`, `5` vs `S`) can occur.
- **Low Confidence Threshold:** Fields with OCR word confidence below 0.60 are marked as **Unable to assess** rather than silently passed.

## 8. Name & Entity Matching
- **Name Matching Calibration:** The in-house Indian phonetic and token-permutation matcher is calibrated on standard synthetic naming structures (initials expansion, honorific removal, token order swaps). It is not an exhaustive national registry lookup.
- **Review Requirement:** Scores in the "Needs Review" band are categorized as **Observations**, requiring human verification, not automated flags.

## 9. Scope of Synthetic Data
- All evaluations and benchmarks are conducted on **synthetic Indian financial and identity documents**. No real customer PII was ingested or evaluated.

## 10. Advisory Nature & Zero-Accusation Policy
- **No Automated Fraud Classification:** The system strictly adheres to advisory terminology. It **never** labels any document or individual as "fraud", "counterfeit", "fake", "forged", or "criminal". It produces factual observations, identifies cross-document inconsistencies, and highlights potential manipulations requiring human investigation.
