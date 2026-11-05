"""
Prompt-Injection and Adversarial Instruction Scanner.
Scans extracted vector text, hidden microscopic/white text spans, and OCR text
for adversarial instruction patterns attempting to manipulate AI reviewers
(e.g., "ignore previous instructions", "this document is genuine", "approve", "do not flag").

Non-negotiable security guarantee:
Adversarial prompt text is strictly quarantined as an Observation finding.
It has zero influence over scoring, arithmetic rules, or case decisions.
"""

import re
from typing import Any, Dict, List, Optional
from backend.app.models.contracts import (
    EvidenceItem,
    Finding,
    FindingCategory,
    FindingStatus,
    FindingStrength,
    FindingTier,
    ReviewerAction,
    BBox,
)

INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"system\s+prompt",
    r"this\s+document\s+is\s+genuine",
    r"do\s+not\s+flag",
    r"approve\s+(?:this\s+)?(?:document|application|case|loan)",
    r"disregard\s+(?:all\s+)?findings",
    r"override\s+instructions",
    r"mark\s+as\s+verified",
    r"bypass\s+(?:verification|checks|forensics)",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
]

COMPILED_INJECTION_REGEX = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def scan_text_for_injections(
    text: str,
    doc_id: str,
    page_num: int = 1,
    bbox: Optional[BBox] = None,
    source_context: str = "extracted text",
) -> List[Finding]:
    """
    Scans a given text string for adversarial prompt injection patterns.
    Returns list of Finding contracts in category INJECTION.
    """
    findings = []
    bbox = bbox or [0, 0, 100, 50]

    for match in COMPILED_INJECTION_REGEX.finditer(text):
        matched_str = match.group(0)
        findings.append(
            Finding(
                finding_id=f"ANM-INJECT-{doc_id}-{page_num}-{match.start()}",
                tier=FindingTier.OBSERVATION,
                category=FindingCategory.INJECTION,
                rule_id="prompt_injection_pattern",
                title=f"Adversarial instruction text detected ('{matched_str}')",
                evidence=[EvidenceItem(doc_id=doc_id, page=page_num, bbox=bbox, label=f"Injection span in {source_context}")],
                signals=["adversarial_prompt_injection"],
                strength=FindingStrength.STRONG,
                confidence=0.98,
                status=FindingStatus.REQUIRES_INVESTIGATION,
                explanation=(
                    f"Document contains adversarial instruction phrasing '{matched_str}' in {source_context}. "
                    "Although this system operates deterministically without an LLM, hidden instruction-like text is a severe red flag "
                    "intended to mislead AI-assisted review tooling or human investigators."
                ),
                reviewer=ReviewerAction(),
            )
        )

    return findings


def scan_spans_for_injections(
    spans: List[Dict[str, Any]],
    doc_id: str,
    page_num: int = 1,
) -> List[Finding]:
    """Scans PyMuPDF span list for injection phrases."""
    findings = []
    for s in spans:
        text = s.get("text", "")
        if not text:
            continue
        raw_bbox = s.get("bbox") or [0, 0, 100, 50]
        # PyMuPDF returns float coords; BBox contract requires int — cast here
        bbox = [int(v) for v in raw_bbox]
        context = "visible span"
        if s.get("color") == 16777215 or s.get("size", 10.0) < 3.0:
            context = "hidden/white text span"

        span_findings = scan_text_for_injections(
            text=text,
            doc_id=doc_id,
            page_num=page_num,
            bbox=bbox,
            source_context=context,
        )
        findings.extend(span_findings)

    return findings
