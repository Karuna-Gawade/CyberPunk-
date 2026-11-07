import { DocumentRecord, ExtractedField, Finding, Investigation, CapabilitiesReport, ReviewDecision, CaseDecisionType, AuditEvent } from '../types';

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string) || 'http://localhost:8000';

export async function createInvestigation(): Promise<Investigation> {
  const res = await fetch(`${API_BASE}/investigations`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to create investigation');
  return res.json();
}

export async function listInvestigations(): Promise<Investigation[]> {
  const res = await fetch(`${API_BASE}/investigations`);
  if (!res.ok) throw new Error('Failed to list investigations');
  return res.json();
}

export async function classifyDocumentWithLlm(
  docId: string,
  apiKey?: string,
  provider: string = 'auto',
): Promise<DocumentRecord> {
  const res = await fetch(`${API_BASE}/documents/${docId}/classify-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey || null, provider }),
  });
  if (!res.ok) throw new Error('Failed to classify document with LLM');
  return res.json();
}

export async function classifyInvestigationWithLlm(
  invId: string,
  apiKey?: string,
  provider: string = 'auto',
): Promise<Investigation> {
  const res = await fetch(`${API_BASE}/investigations/${invId}/classify-llm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey || null, provider }),
  });
  if (!res.ok) throw new Error('Failed to classify investigation with LLM');
  return res.json();
}

export async function uploadDocuments(invId: string, files: File[]): Promise<DocumentRecord[]> {
  const formData = new FormData();
  for (const f of files) {
    formData.append('files', f);
  }
  const res = await fetch(`${API_BASE}/investigations/${invId}/documents`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to upload documents');
  return res.json();
}

export function getStoredLlmApiKey(): string {
  return localStorage.getItem('llm_api_key') || '';
}

export function setStoredLlmApiKey(key: string): void {
  localStorage.setItem('llm_api_key', key);
}

export async function processInvestigation(invId: string): Promise<Investigation> {
  const apiKey = getStoredLlmApiKey();
  const headers: Record<string, string> = {};
  if (apiKey) {
    headers['x-llm-api-key'] = apiKey;
  }
  const res = await fetch(`${API_BASE}/investigations/${invId}/process`, {
    method: 'POST',
    headers,
  });
  if (!res.ok) throw new Error('Failed to process investigation');
  return res.json();
}

export async function getInvestigation(invId: string): Promise<Investigation> {
  const res = await fetch(`${API_BASE}/investigations/${invId}`);
  if (!res.ok) throw new Error('Failed to fetch investigation');
  return res.json();
}

export async function getFindings(invId: string): Promise<Finding[]> {
  const res = await fetch(`${API_BASE}/investigations/${invId}/findings`);
  if (!res.ok) throw new Error('Failed to fetch findings');
  return res.json();
}

export async function getDocumentFields(docId: string): Promise<ExtractedField[]> {
  const res = await fetch(`${API_BASE}/documents/${docId}/fields`);
  if (!res.ok) throw new Error('Failed to fetch fields');
  return res.json();
}

export async function revealField(fieldId: string): Promise<{ field_id: string; unmasked_value: any }> {
  const res = await fetch(`${API_BASE}/fields/${fieldId}/reveal`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to reveal field');
  return res.json();
}

export async function getCapabilities(): Promise<CapabilitiesReport> {
  const res = await fetch(`${API_BASE}/capabilities`);
  if (!res.ok) throw new Error('Failed to fetch capabilities');
  return res.json();
}

export function getDocumentPageImageUrl(docId: string, pageNum: number): string {
  return `${API_BASE}/documents/${docId}/pages/${pageNum}/image`;
}

// Phase 5: Human Review endpoints

export async function reviewFinding(
  findingId: string,
  decision: ReviewDecision,
  reason: string,
  reviewerId: string = 'OFFICER-DEFAULT',
): Promise<Finding> {
  const res = await fetch(`${API_BASE}/findings/${findingId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reason, reviewer_id: reviewerId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || 'Failed to review finding');
  }
  return res.json();
}

export async function recordCaseDecision(
  invId: string,
  decision: CaseDecisionType,
  outcomeNote: string,
  decidedBy: string = 'OFFICER-DEFAULT',
): Promise<Investigation> {
  const res = await fetch(`${API_BASE}/investigations/${invId}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, outcome_note: outcomeNote, decided_by: decidedBy }),
  });
  if (!res.ok) throw new Error('Failed to record case decision');
  return res.json();
}

export function getDossierUrl(invId: string): string {
  return `${API_BASE}/investigations/${invId}/dossier`;
}

export async function getAuditTrail(invId: string): Promise<AuditEvent[]> {
  const res = await fetch(`${API_BASE}/investigations/${invId}/audit`);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

export async function verifyAuditChain(invId: string): Promise<{ chain_valid: boolean; broken_at_seq: number | null }> {
  const res = await fetch(`${API_BASE}/investigations/${invId}/audit/verify`);
  if (!res.ok) throw new Error('Failed to verify audit chain');
  return res.json();
}
