import React, { useState, useEffect } from 'react';
import { Finding, BBox, ReviewDecision, CaseDecisionType, Investigation } from '../types';
import { FindingCard } from '../components/FindingCard';
import { getFindings, reviewFinding, recordCaseDecision, getDossierUrl, getInvestigation } from '../api/client';

interface FindingsViewProps {
  investigationId: string;
  onJumpToEvidence: (docId: string, page: number, bbox: BBox) => void;
}

export const FindingsView: React.FC<FindingsViewProps> = ({
  investigationId,
  onJumpToEvidence,
}) => {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Case Decision State
  const [decisionModalOpen, setDecisionModalOpen] = useState(false);
  const [caseDecisionType, setCaseDecisionType] = useState<CaseDecisionType>('rely_on_tool_output');
  const [outcomeNote, setOutcomeNote] = useState('');
  const [decidedBy, setDecidedBy] = useState('OFFICER-01');
  const [submittingDecision, setSubmittingDecision] = useState(false);

  const loadData = async () => {
    if (!investigationId) return;
    try {
      const [fData, invData] = await Promise.all([
        getFindings(investigationId),
        getInvestigation(investigationId),
      ]);
      setFindings(fData);
      setInvestigation(invData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [investigationId]);

  const handleReviewFinding = async (findingId: string, decision: ReviewDecision, reason: string) => {
    await reviewFinding(findingId, decision, reason, decidedBy);
    await loadData();
  };

  const handleRecordCaseDecision = async () => {
    if (!outcomeNote.trim()) {
      alert('Outcome note is required.');
      return;
    }
    setSubmittingDecision(true);
    try {
      const updatedInv = await recordCaseDecision(investigationId, caseDecisionType, outcomeNote, decidedBy);
      setInvestigation(updatedInv);
      setDecisionModalOpen(false);
    } catch (err: any) {
      alert(err.message || 'Failed to record decision');
    } finally {
      setSubmittingDecision(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>Loading investigation findings...</div>;
  }

  return (
    <div style={{ maxWidth: '1000px', margin: '20px auto' }}>
      {/* Header with Case Status & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '18px', color: '#f8fafc', margin: '0 0 4px 0' }}>
            Investigation Findings ({findings.length})
          </h2>
          <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0 }}>
            Deterministic rule results and multi-signal anomalies requiring human investigation.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={() => window.open(getDossierUrl(investigationId), '_blank')}
            style={{
              backgroundColor: '#0284c7',
              color: '#ffffff',
              border: 'none',
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>Download Dossier PDF</span>
            {investigation?.case_decision ? (
              <span style={{ fontSize: '10px', backgroundColor: '#0369a1', padding: '1px 5px', borderRadius: '3px' }}>FINAL</span>
            ) : (
              <span style={{ fontSize: '10px', backgroundColor: '#b45309', padding: '1px 5px', borderRadius: '3px' }}>DRAFT</span>
            )}
          </button>

          <button
            onClick={() => setDecisionModalOpen(true)}
            style={{
              backgroundColor: investigation?.case_decision ? '#1e293b' : '#16a34a',
              color: '#ffffff',
              border: `1px solid ${investigation?.case_decision ? '#475569' : '#22c55e'}`,
              padding: '6px 14px',
              borderRadius: '6px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            {investigation?.case_decision ? 'Update Case Decision' : 'Record Case Decision'}
          </button>
        </div>
      </div>

      {/* Case Decision Banner if present */}
      {investigation?.case_decision && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #3b82f6', borderRadius: '8px', padding: '14px', marginBottom: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '13px', fontWeight: '700', color: '#60a5fa' }}>
              Human Case Decision Recorded: {investigation.case_decision.decision.replace(/_/g, ' ').toUpperCase()}
            </span>
            <span style={{ fontSize: '11px', color: '#94a3b8' }}>
              Decided by {investigation.case_decision.decided_by} at {investigation.case_decision.decided_at.slice(0, 19)}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '12px', color: '#cbd5e1' }}>
            <strong>Note:</strong> {investigation.case_decision.outcome_note}
          </p>
        </div>
      )}

      {/* Case Decision Modal */}
      {decisionModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{ backgroundColor: '#1e293b', border: '1px solid #475569', borderRadius: '8px', padding: '24px', width: '500px', maxWidth: '90%' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '16px', color: '#f8fafc' }}>Record Final Case Decision</h3>
            <p style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '16px', lineHeight: '1.4' }}>
              The system operates in advisory mode. You may choose to rely on, partially rely on, or completely disregard the automated findings.
            </p>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: '#cbd5e1', marginBottom: '6px' }}>Decision Choice:</label>
              <select
                value={caseDecisionType}
                onChange={(e) => setCaseDecisionType(e.target.value as CaseDecisionType)}
                style={{ width: '100%', padding: '8px', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '4px', color: '#fff', fontSize: '13px' }}
              >
                <option value="rely_on_tool_output">Rely on Tool Output</option>
                <option value="partially_rely">Partially Rely on Output</option>
                <option value="disregard_tool_output">Disregard Tool Output Entirely</option>
                <option value="needs_more_information">Needs More Information / Pending</option>
              </select>
            </div>

            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: '#cbd5e1', marginBottom: '6px' }}>Investigator ID / Name:</label>
              <input
                type="text"
                value={decidedBy}
                onChange={(e) => setDecidedBy(e.target.value)}
                style={{ width: '100%', padding: '8px', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '4px', color: '#fff', fontSize: '13px', boxSizing: 'border-box' }}
              />
            </div>

            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: '#cbd5e1', marginBottom: '6px' }}>Investigator Outcome Note (Mandatory):</label>
              <textarea
                rows={3}
                placeholder="Explain the reasoning behind the final case determination..."
                value={outcomeNote}
                onChange={(e) => setOutcomeNote(e.target.value)}
                style={{ width: '100%', padding: '8px', backgroundColor: '#0f172a', border: '1px solid #475569', borderRadius: '4px', color: '#fff', fontSize: '13px', boxSizing: 'border-box' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDecisionModalOpen(false)}
                style={{ backgroundColor: 'transparent', border: '1px solid #475569', color: '#cbd5e1', padding: '6px 14px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
              >
                Cancel
              </button>
              <button
                disabled={submittingDecision || !outcomeNote.trim()}
                onClick={handleRecordCaseDecision}
                style={{
                  backgroundColor: '#16a34a', border: 'none', color: '#fff', padding: '6px 14px', borderRadius: '4px',
                  fontWeight: '600', cursor: submittingDecision || !outcomeNote.trim() ? 'not-allowed' : 'pointer', fontSize: '12px',
                  opacity: !outcomeNote.trim() ? 0.5 : 1
                }}
              >
                Submit Decision
              </button>
            </div>
          </div>
        </div>
      )}

      {findings.length === 0 ? (
        <div
          style={{
            backgroundColor: '#1e293b',
            border: '1px solid #064e3b',
            borderRadius: '8px',
            padding: '40px',
            textAlign: 'center',
            color: '#34d399',
          }}
        >
          <div style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>
            Zero Inconsistencies or Anomalies Detected
          </div>
          <div style={{ fontSize: '13px', color: '#94a3b8' }}>
            All internal mathematical checks, entity correlations, and cross-document fields match cleanly.
          </div>
        </div>
      ) : (
        findings.map((f) => (
          <FindingCard
            key={f.finding_id}
            finding={f}
            onSelectEvidence={(idx) => {
              const ev = f.evidence[idx];
              if (ev && ev.bbox) {
                onJumpToEvidence(ev.doc_id, ev.page, ev.bbox);
              }
            }}
            onReview={handleReviewFinding}
          />
        ))
      )}
    </div>
  );
};
