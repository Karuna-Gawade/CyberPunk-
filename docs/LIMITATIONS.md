# System Limitations & Boundary Conditions

In alignment with forensic reporting standards (ISO/IEC 27037, 27041, 27042, NIST SP 800-86), this document outlines the operational boundaries, known limitations, and non-supported capabilities of the AI Document Forensics System.

## 1. Cryptographic Signature Verification
- **UIDAI Aadhaar Digital Signature:** The system extracts and decodes the demographic payload from the Aadhaar Secure QR code (zlib-compressed big-integer format), but **does not verify the cryptographic X.509 UIDAI PKI signature**. Offline systems without live certificate revocation lists (CRL) cannot guarantee public-key validity without government root keys.
- **Bank Statement Digital Signatures:** PDF digital signatures (DocuSign, Adobe Sign, etc.) are verified for metadata anomalies and revisions (`%%EOF`), but cryptographic trust chain validation against external trust lists is out of scope for offline operation.

## 2. Image Forensics as Weak Supporting Signals
- **Error Level Analysis (ELA):** ELA detects compression differences across JPEG blocks. However, normal multiple saves, WhatsApp/messaging re-compression, and scanner downsampling naturally cause high ELA variations. ELA is treated strictly as a **weak supporting signal** and can never alone escalate an issue beyond an **Observation**.
- **Copy-Move & Noise Inconsistency:** Heavy blurring or aggressive scanner binarization can mask copy-move artifacts or create false block matches.

## 3. OCR Engine Accuracy & Physical Scans
- **Tesseract Limitations:** Tesseract 5.x performance depends on document resolution, deskew quality, and contrast. On low-resolution scans (<150 DPI) or handwritten forms, character confusion (e.g., `0` vs `O`, `1` vs `l`, `5` vs `S`) can occur.
- **Low Confidence Threshold:** Fields with OCR word confidence below 0.60 are marked as **Unable to assess** rather than silently passed.

## 4. Name & Entity Matching
- **Name Matching Calibration:** The in-house Indian phonetic and token-permutation matcher is calibrated on standard synthetic naming structures (initials expansion, honorific removal, token order swaps). It is not an exhaustive national registry lookup.
- **Review Requirement:** Scores in the "Needs Review" band are categorized as **Observations**, requiring human verification, not automated flags.

## 5. Scope of Synthetic Data
- All evaluations and benchmarks are conducted on **synthetic Indian financial and identity documents**. No real customer PII was ingested or evaluated. Real-world documents may exhibit variations in proprietary bank statement layouts.

## 6. Advisory Nature
- **No Automated Fraud Classification:** The system never labels any document as "fraud", "counterfeit", or "forged". It produces factual observations, identifies cross-document inconsistencies, and highlights potential manipulations requiring human investigation.
