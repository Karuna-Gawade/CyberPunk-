# Architectural Decisions Log

This document records technical and architectural decisions made during the implementation of the AI Document Forensics and Contextual Intelligence System (PS-2), following the principle of deterministic detection with human oversight.

| ID | Date | Decision | Rationale | Alternatives Considered |
|---|---|---|---|---|
| DEC-001 | 2026-11-05 | Fully offline deterministic architecture | System must operate in secure, air-gapped forensic environments with no external API leakage. | Cloud AI / LLMs (prohibited by spec) |
| DEC-002 | 2026-11-05 | Single stored coordinate system at fixed 150 DPI | Consistent UI overlay and bounding-box representation across PyMuPDF rendering (150 DPI) and Tesseract OCR (run at 300 DPI, scaled by 0.5). | Raw PDF points or normalized 0-1 coordinates (prone to aspect ratio drift in mixed scan/vector documents). |
| DEC-003 | 2026-11-05 | Pure functional rules engine (`RuleResult`) | Every deterministic rule is a side-effect-free pure function returning pass/fail/not_applicable, making rule evaluation robust against missing data. | Monolithic rule engine with embedded database queries. |
| DEC-004 | 2026-11-05 | Deterministic explanation templates | Explanations must strictly reflect the evidence that triggered the rule; zero hallucinated facts and no prohibited wording ("fraud", "forged"). | Natural language generation (uncontrollable and non-deterministic). |
| DEC-005 | 2026-11-05 | In-house fuzzy name matcher (stdlib difflib + Jaro-Winkler) | Avoid prohibited external dependencies (`rapidfuzz`, etc.) while correctly handling Indian naming conventions, token swaps, and initials. | External fuzzy libraries (violates third-party policy). |
| DEC-006 | 2026-11-05 | Mandatory human Case Decision | System remains strictly advisory. Watermark dossier as DRAFT until a human explicitly records a case decision. | Auto-approving or flagging cases automatically (violates human-in-the-loop requirement). |
| DEC-007 | 2026-11-05 | Hash-chained audit trail | Append-only sequence using SHA-256 over canonical JSON of previous and current entries to detect any tampering with audit logs. | Unsigned relational DB logging. |
