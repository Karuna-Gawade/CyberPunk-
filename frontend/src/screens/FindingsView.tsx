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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)', margin: '0 0 4px 0' }}>
            Investigation Findings ({findings.length})
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0, fontFamily: 'var(--font-mono)' }}>
            Deterministic rule results and multi-signal anomalies requiring human investigation.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={() => window.open(getDossierUrl(investigationId), '_blank')}
            className="btn-action btn-accent"
            style={{ fontSize: '11px', padding: '5px 12px' }}
          >
            <span>Download Dossier PDF</span>
            {investigation?.case_decision ? (
              <span style={{ fontSize: '9px', backgroundColor: 'rgba(255,255,255,0.2)', padding: '1px 4px', borderRadius: '2px', fontFamily: 'var(--font-mono)' }}>FINAL</span>
            ) : (
              <span style={{ fontSize: '9px', backgroundColor: 'var(--tier-incons)', padding: '1px 4px', borderRadius: '2px', fontFamily: 'var(--font-mono)' }}>DRAFT</span>
            )}
          </button>

          <button
            onClick={() => setDecisionModalOpen(true)}
            className="btn-action"
            style={{ fontSize: '11px', padding: '5px 12px' }}
          >
            {investigation?.case_decision ? 'Update Case Decision' : 'Record Case Decision'}
          </button>
        </div>
      </div>

      {/* Case Decision Banner if present */}
      {investigation?.case_decision && (
        <div className="panel" style={{ padding: '12px 16px', marginBottom: '16px', borderLeft: '4px solid var(--accent-main)', backgroundColor: 'var(--bg-subtle)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <span style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
              HUMAN CASE DECISION: {investigation.case_decision.decision.replace(/_/g, ' ').toUpperCase()}
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Decided by {investigation.case_decision.decided_by} at {investigation.case_decision.decided_at.slice(0, 19)}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '12.5px', color: 'var(--text-main)' }}>
            <strong>Note:</strong> {investigation.case_decision.outcome_note}
          </p>
        </div>
      )}

      {/* Case Decision Modal */}
      {decisionModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div className="panel" style={{ padding: '20px', width: '480px', maxWidth: '90%', backgroundColor: 'var(--bg-panel)' }}>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '15px', fontWeight: '700', color: 'var(--text-main)' }}>Record Final Case Decision</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '14px', lineHeight: '1.4' }}>
              The system operates in advisory mode. You may choose to rely on, partially rely on, or completely disregard the automated findings.
            </p>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>Decision Choice:</label>
              <select
                value={caseDecisionType}
                onChange={(e) => setCaseDecisionType(e.target.value as CaseDecisionType)}
                style={{ width: '100%', padding: '6px 8px', backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--text-main)', fontSize: '12px', fontFamily: 'var(--font-sans)' }}
              >
                <option value="rely_on_tool_output">Rely on Tool Output</option>
                <option value="partially_rely">Partially Rely on Output</option>
                <option value="disregard_tool_output">Disregard Tool Output Entirely</option>
                <option value="needs_more_information">Needs More Information / Pending</option>
              </select>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>Investigator ID / Name:</label>
              <input
                type="text"
                value={decidedBy}
                onChange={(e) => setDecidedBy(e.target.value)}
                style={{ width: '100%', padding: '6px 8px', backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--text-main)', fontSize: '12px', boxSizing: 'border-box', fontFamily: 'var(--font-sans)' }}
              />
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>Investigator Outcome Note (Mandatory):</label>
              <textarea
                rows={3}
                placeholder="Explain the reasoning behind the final case determination..."
                value={outcomeNote}
                onChange={(e) => setOutcomeNote(e.target.value)}
                style={{ width: '100%', padding: '6px 8px', backgroundColor: 'var(--bg-panel)', border: '1px solid var(--border-color)', borderRadius: '4px', color: 'var(--text-main)', fontSize: '12px', boxSizing: 'border-box', fontFamily: 'var(--font-sans)' }}
              />
            </div>

            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDecisionModalOpen(false)}
                className="btn-action"
              >
                Cancel
              </button>
              <button
                disabled={submittingDecision || !outcomeNote.trim()}
                onClick={handleRecordCaseDecision}
                className="btn-action btn-accent"
              >
                Submit Decision
              </button>
            </div>
          </div>
        </div>
      )}

      {findings.length === 0 ? (
        <div
          className="panel"
          style={{
            padding: '36px',
            textAlign: 'center',
            color: 'var(--text-muted)',
          }}
        >
          <div style={{ fontSize: '14px', fontWeight: '700', marginBottom: '6px', color: 'var(--text-main)' }}>
            Zero Inconsistencies or Anomalies Detected
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
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
