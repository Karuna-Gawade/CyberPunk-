from __future__ import annotations
from enum import Enum
from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    AADHAAR = "aadhaar"
    PAN = "pan"
    SALARY_SLIP = "salary_slip"
    BANK_STATEMENT = "bank_statement"
    UNSUPPORTED = "unsupported"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    UNSUPPORTED = "unsupported"
    ERROR = "error"
    ENCRYPTED = "encrypted"
    OCR_FAILED = "ocr_failed"


class FieldSource(str, Enum):
    OCR = "ocr"
    TEXT_LAYER = "text_layer"
    QR = "qr"


class FindingTier(str, Enum):
    OBSERVATION = "observation"
    INCONSISTENCY = "inconsistency"
    POTENTIAL_MANIPULATION = "potential_manipulation"


class FindingCategory(str, Enum):
    WITHIN_DOCUMENT = "within_document"
    CROSS_DOCUMENT = "cross_document"
    FORENSIC = "forensic"
    INJECTION = "injection"
    SYSTEM = "system"


class FindingStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class FindingStatus(str, Enum):
    REQUIRES_INVESTIGATION = "requires_investigation"
    CONFIRMED_BY_REVIEWER = "confirmed_by_reviewer"
    DISMISSED = "dismissed"


class ReviewDecision(str, Enum):
    CONFIRM = "confirm"
    DISMISS = "dismiss"
    ESCALATE = "escalate"


class CaseDecisionType(str, Enum):
    RELY_ON_TOOL_OUTPUT = "rely_on_tool_output"
    PARTIALLY_RELY = "partially_rely"
    DISREGARD_TOOL_OUTPUT = "disregard_tool_output"
    NEEDS_MORE_INFORMATION = "needs_more_information"


class ReviewPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RuleStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


# Bounding Box: [x0, y0, x1, y1] in fixed 150 DPI coordinate system, origin top-left
BBox = List[int]


class ExtractedField(BaseModel):
    field_id: str
    doc_id: str
    name: str
    value: Any
    raw_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: FieldSource
    page: int = Field(ge=1)
    bbox: BBox
    unable_to_assess: bool = False


class DocumentRecord(BaseModel):
    doc_id: str
    filename: str
    sha256: str
    type: DocumentType = DocumentType.UNSUPPORTED
    type_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    pages: int = 1
    render_dpi: int = 150
    status: DocumentStatus = DocumentStatus.UPLOADED
    error_message: Optional[str] = None
    fields: List[ExtractedField] = []


class EvidenceItem(BaseModel):
    doc_id: str
    field_id: Optional[str] = None
    page: int = Field(ge=1)
    bbox: BBox
    label: Optional[str] = None


class ReviewerAction(BaseModel):
    decision: Optional[ReviewDecision] = None
    reason: Optional[str] = None
    by: Optional[str] = None
    at: Optional[str] = None


class Finding(BaseModel):
    finding_id: str
    tier: FindingTier
    category: FindingCategory
    rule_id: str
    title: str
    evidence: List[EvidenceItem]
    signals: List[str]
    strength: FindingStrength
    confidence: float = Field(ge=0.0, le=1.0)
    status: FindingStatus = FindingStatus.REQUIRES_INVESTIGATION
    explanation: str = ""
    reviewer: ReviewerAction = Field(default_factory=ReviewerAction)


class PriorityBreakdownItem(BaseModel):
    rule_id: str
    title: str
    points: int
    tier: FindingTier


class CaseDecision(BaseModel):
    decision: CaseDecisionType
    outcome_note: str
    decided_by: str
    decided_at: str
    findings_reviewed: int


class AuditEvent(BaseModel):
    seq: int
    timestamp: str
    investigation_id: str
    actor: str
    action: str
    object_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    entry_hash: str


class Investigation(BaseModel):
    investigation_id: str
    created_at: str
    documents: List[DocumentRecord] = []
    review_priority: ReviewPriority = ReviewPriority.LOW
    priority_score: int = 0
    priority_breakdown: List[PriorityBreakdownItem] = []
    case_decision: Optional[CaseDecision] = None


class RuleResult(BaseModel):
    rule_id: str
    result: RuleStatus
    field_ids_used: List[str] = []
    detail: str
    signals: List[str] = []
    evidence: List[EvidenceItem] = []
    tier: Optional[FindingTier] = None
    strength: Optional[FindingStrength] = None
    title: Optional[str] = None


class CapabilityStatus(BaseModel):
    feature: str
    status: str  # "implemented" | "partial" | "planned" | "unsupported"
    detail: str


class CapabilitiesReport(BaseModel):
    tesseract_available: bool
    tesseract_version: Optional[str]
    tesseract_languages: List[str]
    system_mode: str = "offline"
    capabilities: List[CapabilityStatus]
