# 5-Minute Hackathon Demo Script: AI Document Forensics & Contextual Intelligence System (PS-2)

**Presenters:** Lead Full-Stack & Forensics Engineers  
**Target Audience:** Hackathon Judges & Security Evaluators  
**Key Guiding Principle:** *Deterministic code detects; nothing AI-decides. The human makes every final decision.*

---

## ⏱️ Minute 0:00 – 1:00 | System Architecture & Classification Engine
1. **Open the Web Application:**
   - Highlight the persistent advisory banner at the top of every screen:
     > *"Advisory output. Final decision rests with the human reviewer."*
   - Point out the status badge: **"Offline Mode"** (100% offline, zero cloud calls, zero external LLMs).
2. **Navigate to "Capabilities" Tab:**
   - Review the system support matrix:
     - 🚀 **Two-Stage Classifier:** Supervised **XGBoost ML model** (99.88% 5-fold CV accuracy over TF-IDF n-grams) with heuristic layout fallback.
     - 📂 **7 Document Classes:** Aadhaar, PAN, Salary Slip, Bank Statement, Loan Application, Form 15G Declaration, and Payment Instructions.
     - 📄 **Multi-Format Ingestion:** Native ingestion for `.pdf`, `.docx`, `.xlsx`, `.png`, `.jpg`, `.tiff`, and `.webp` with 422 HTTP validation.
     - 🔍 **Visual Forensics:** Signature presence/overlap, baseline displacement, font inconsistencies, incremental `%%EOF` re-saves, hidden text, and ELA.
     - 🛡️ **Defenses:** Prompt-injection quarantine, Verhoeff checksum, PII masking, and hash-chained SHA-256 audit ledger.

---

## ⏱️ Minute 1:00 – 2:00 | Ingestion & Clean 7-Document Bundle (`genuine_06`)
1. **Upload Complete 7-Document Bundle (`samples/bundles/genuine_06`):**
   - Upload Aadhaar, PAN, Salary Slip, Bank Statement, Loan Application, Form 15G, and Payment Instruction.
   - Show instantaneous client-side SHA-256 calculation and server rendering to 150 DPI.
2. **Review Zero False-Positive Performance:**
   - Run processing: the system classifies all 7 documents with **99.4%–99.79% XGBoost confidence**.
   - Show that `genuine_06` yields **0 findings** and **LOW review priority (0 score)**.
3. **PII Protection & Audited Reveal:**
   - Open Document View: Aadhaar (`XXXX XXXX 5674`) and PAN are masked.
   - Click "Reveal" on an officer workstation: the value is shown and an audit event (`pii_revealed`) is logged to the cryptographic chain.

---

## ⏱️ Minute 2:00 – 3:15 | Cross-Document Intelligence & New Attack Scenarios
1. **Demo Scenario A: Income Inflation (`tampered_11_income_inflate`):**
   - Upload bundle `tampered_11_income_inflate`.
   - Point out **Cross-Document Finding (`ANM-LOAN-INC`)**: Applicant declared monthly income of INR 185,000.00 on the Loan Application, but their verified Salary Slip shows gross earnings of only INR 85,200.00.
   - Click the two-sided evidence link to highlight both documents side by side in the viewer.
2. **Demo Scenario B: Tax Exemption Concealment (`tampered_12_15g_income`):**
   - Show Form 15G declaring annual income of INR 240,000.00 to evade TDS, directly conflicting with annualized payroll gross of INR 1,200,000.00.
3. **Demo Scenario C: Phantom Payment Debit (`tampered_13_payment_absent`):**
   - Show Payment Transfer Instruction specifying an INR 50,000.00 debit mandate, which has zero matching debit entry in the bank statement transactions table.

---

## ⏱️ Minute 3:15 – 4:00 | Visual Forensics & Signal Convergence
1. **Signature Verification & Overlap Detection:**
   - Demonstrate the signature region check: detects when a signature line is completely empty (`signature_region_empty`), or when a drawn signature mark intrudes into and overlaps data fields (`signature_placement_overlap`).
2. **Baseline Alignment Forensics:**
   - Show baseline disparity detection (`baseline_alignment_anomaly`): detects when spliced text inserts exhibit a vertical origin displacement > 3pt along the same row.
3. **Signal Convergence & Linked Findings (`related_finding_ids`):**
   - Point out how a visual font anomaly and a numeric cross-doc discrepancy occurring on the same bounding region are linked via `related_finding_ids`, escalating review priority.

---

## ⏱️ Minute 4:00 – 5:00 | Human Review, Audit Chain & PS-2 §7 Dossier Export
1. **Human Decision Workflow:**
   - Demonstrate finding review actions: **Confirm**, **Escalate**, or **Dismiss** (requires mandatory reason).
   - Click **"Record Case Decision"**: Select *"Partially Rely"* or *"Rely on Tool Output"*, record officer rationale, and submit.
2. **Cryptographic Hash Chain Verification:**
   - Run audit verification (`GET /investigations/{id}/audit/verify`) proving the SHA-256 chain is 100% valid.
3. **Section 7 Structured Dossier Export:**
   - Download the generated dossier PDF (or inspect `docs/sample_dossier.pdf`).
   - Walk through the exact Section 7 layout:
     - **7.1 Document Overview:** File names, types, hashes, page counts.
     - **7.2 Extracted Information:** Form fields with strict PII masking.
     - **7.3 Contextual Analysis:** Multi-entity cross-document comparison matrix.
     - **7.4 Visual Forensic Findings:** Font deviations, ELA, incremental updates, and signatures.
     - **7.5 Evidence and Traceability:** Cropped high-resolution thumbnails with bounding box overlays and linked findings.
     - **7.6 Investigation Summary:** Overall review priority, score breakdown, and human case decision.
