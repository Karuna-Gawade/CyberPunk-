export type DocumentType =
  | 'aadhaar'
  | 'pan'
  | 'salary_slip'
  | 'bank_statement'
  | 'loan_application'
  | 'declaration_15g'
  | 'payment_instruction'
  | 'unsupported';

export type DocumentStatus =
  | 'uploaded'
  | 'processing'
  | 'processed'
  | 'unsupported'
  | 'error'
  | 'encrypted'
  | 'ocr_failed';

export type FieldSource = 'ocr' | 'text_layer' | 'qr';

export type FindingTier = 'observation' | 'inconsistency' | 'potential_manipulation';

export type FindingCategory =
  | 'within_document'
  | 'cross_document'
  | 'forensic'
  | 'injection'
  | 'system';

export type FindingStrength = 'weak' | 'moderate' | 'strong';

export type FindingStatus =
  | 'requires_investigation'
  | 'confirmed_by_reviewer'
  | 'dismissed';

export type ReviewDecision = 'confirm' | 'dismiss' | 'escalate';

export type CaseDecisionType =
  | 'rely_on_tool_output'
  | 'partially_rely'
  | 'disregard_tool_output'
  | 'needs_more_information';

export type ReviewPriority = 'low' | 'medium' | 'high';

export type BBox = [number, number, number, number]; // [x0, y0, x1, y1] at 150 DPI

export interface ExtractedField {
  field_id: string;
  doc_id: string;
  name: string;
  value: any;
  raw_text: string;
  confidence: number;
  source: FieldSource;
  page: number;
  bbox: BBox;
  unable_to_assess?: boolean;
}

export interface DocumentRecord {
  doc_id: string;
  filename: string;
  sha256: string;
  type: DocumentType;
  type_confidence: number;
  llm_type?: DocumentType | null;
  llm_accuracy?: number | null;
  llm_reasoning?: string | null;
  llm_provider?: string | null;
  pages: number;
  render_dpi: number;
  status: DocumentStatus;
  error_message?: string | null;
  fields: ExtractedField[];
}

export interface EvidenceItem {
  doc_id: string;
  field_id?: string | null;
  page: number;
  bbox: BBox;
  label?: string | null;
}

export interface ReviewerAction {
  decision?: ReviewDecision | null;
  reason?: string | null;
  by?: string | null;
  at?: string | null;
}

export interface Finding {
  finding_id: string;
  tier: FindingTier;
  category: FindingCategory;
  rule_id: string;
  title: string;
  evidence: EvidenceItem[];
  signals: string[];
  strength: FindingStrength;
  confidence: number;
  status: FindingStatus;
  explanation: string;
  reviewer: ReviewerAction;
  related_finding_ids?: string[];
}

export interface PriorityBreakdownItem {
  rule_id: string;
  title: string;
  points: number;
  tier: FindingTier;
}

export interface CaseDecision {
  decision: CaseDecisionType;
  outcome_note: string;
  decided_by: string;
  decided_at: string;
  findings_reviewed: number;
}

export interface AuditEvent {
  seq: number;
  timestamp: string;
  investigation_id: string;
  actor: string;
  action: string;
  object_id: string;
  details: Record<string, any>;
  prev_hash: string;
  entry_hash: string;
}

export interface Investigation {
  investigation_id: string;
  created_at: string;
  documents: DocumentRecord[];
  review_priority: ReviewPriority;
  priority_score: number;
  priority_breakdown: PriorityBreakdownItem[];
  case_decision?: CaseDecision | null;
}

export interface CapabilityStatus {
  feature: string;
  status: 'implemented' | 'partial' | 'planned' | 'unsupported';
  detail: string;
}

export interface CapabilitiesReport {
  tesseract_available: boolean;
  tesseract_version?: string | null;
  tesseract_languages: string[];
  system_mode: string;
  capabilities: CapabilityStatus[];
}

export interface CrossDocComparisonField {
  field_name: string;
  status: 'match' | 'conflict' | 'needs_review' | 'not_applicable';
  score?: number | null;
  docs: Array<{
    doc_id: string;
    doc_type: DocumentType;
    value: string;
    field_id?: string;
    bbox?: BBox;
    page?: number;
  }>;
  finding_id?: string | null;
}
