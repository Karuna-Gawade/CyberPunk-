# Review Priority Scoring & Points Justification

The Review Priority (`Low`, `Medium`, `High`) is an advisory queue-sorting mechanism designed to direct human investigator attention where conflicting evidence is most concentrated. It is **NOT** a probability of fraud, nor does it represent an automated verdict.

## 1. Points Matrix

| Signal / Rule Category | Points | Justification |
|---|---|---|
| **Salary Arithmetic Failure** (`salary_net_pay_calc`) | 25 | Internal mathematical contradiction within an official payroll record indicates high likelihood of manual tampering. |
| **Bank Running Balance Continuity Break** (`bank_balance_continuity`) | 30 | Ledger math break in bank transaction rows is a strong indicator of edited or deleted transaction records. |
| **Cross-Document Salary Credit Mismatch** (`salary_credit_match`) | 25 | Mismatch between declared net pay on slip and actual credited deposit in bank statement. |
| **DOB Mismatch Across Documents** (`dob_match`) | 20 | Conflicting birth dates across official government IDs (PAN vs Aadhaar) indicates either clerical error or synthetic identity creation. |
| **Name Conflict Across Documents** (`name_match_conflict`) | 15 | Significant phonetic or structural divergence in full names after accounting for honorifics, token swaps, and initials. |
| **Name Needs Review** (`name_match_review`) | 5 | Minor spelling variation, transliteration difference, or ambiguous initial expansion. |
| **Aadhaar QR Demographic Mismatch** (`aadhaar_qr_text_mismatch`) | 35 | Strong evidence: printed OCR demographic data contradicts the tamper-resistant QR code payload on the same document. |
| **PDF-Native Metadata Anomaly** (`producer_editing_tool`) | 10 | Consumer editing software (Photoshop, Canva, Sejda, iLovePDF) found in creator metadata of institutional financial statements. |
| **PDF Multiple Re-saves** (`incremental_updates_flag`) | 10 | Multiple `%%EOF` markers indicating post-generation structural modifications. |
| **Font Inconsistency in Sibling Spans** (`font_anomaly`) | 20 | Numerical field formatted in a font/size differing from table header or neighboring rows. |
| **Text-Layer vs OCR Mismatch** (`layer_ocr_mismatch`) | 25 | Underlying searchable text contradicts visible rasterized glyphs (classic overlay tampering). |
| **Hidden Prompt-Injection / Instruction Spans** (`prompt_injection_pattern`) | 20 | Adversarial instructions hidden within white-on-white text, micro-fonts, or off-page boxes. |
| **Image Forensics Supporting Anomaly** (`ela_discontinuity` / `noise_variance`) | 5 | Weak supporting signal; cannot trigger high priority on its own without corroboration. |

## 2. Priority Band Thresholds

- **High Priority** ($\ge 45$ points): Multiple independent conflicting signals or severe mathematical/ledger discontinuities. Requires prioritized review.
- **Medium Priority** ($20 - 44$ points): Clear discrepancy present in a single primary field (e.g., DOB conflict or salary arithmetic mismatch).
- **Low Priority** ($< 20$ points): Only minor observations (e.g., editing software metadata or phonetic name variance) with clean underlying math and consistent identity records.
