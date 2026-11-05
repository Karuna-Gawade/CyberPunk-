import React, { useState } from 'react';
import { Finding, ReviewDecision } from '../types';

interface FindingCardProps {
  finding: Finding;
  onSelectEvidence?: (evidenceIndex: number) => void;
  onReview?: (findingId: string, decision: ReviewDecision, reason: string) => Promise<void>;
}

export const FindingCard: React.FC<FindingCardProps> = ({ finding, onSelectEvidence, onReview }) => {
  const [showDismissModal, setShowDismissModal] = useState(false);
  const [dismissReason, setDismissReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'potential_manipulation':
        return { bg: '#450a0a', text: '#f87171', border: '#b91c1c' };
      case 'inconsistency':
        return { bg: '#422006', text: '#fbbf24', border: '#d97706' };
      case 'observation':
      default:
        return { bg: '#172554', text: '#60a5fa', border: '#2563eb' };
    }
  };

  const getStatusBadge = () => {
    if (finding.status === 'confirmed_by_reviewer') {
      return { bg: '#14532d', text: '#4ade80', border: '#16a34a', label: 'Confirmed by Reviewer' };
    }
    if (finding.status === 'dismissed') {
      return { bg: '#374151', text: '#9ca3af', border: '#4b5563', label: 'Dismissed' };
    }
    return { bg: '#0f172a', text: '#38bdf8', border: '#0284c7', label: 'Requires investigation' };
  };

  const colors = getTierColor(finding.tier);
  const statusBadge = getStatusBadge();

  const handleAction = async (decision: ReviewDecision, reason: string = '') => {
    if (!onReview) return;
    setSubmitting(true);
    try {
      await onReview(finding.finding_id, decision, reason);
      setShowDismissModal(false);
      setDismissReason('');
    } catch (err: any) {
      alert(err.message || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        backgroundColor: '#1e293b',
        border: `1px solid ${colors.border}`,
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '12px',
        color: '#f8fafc',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span
            style={{
              backgroundColor: colors.bg,
              color: colors.text,
              border: `1px solid ${colors.border}`,
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: '700',
              textTransform: 'uppercase',
            }}
          >
            {finding.tier.replace('_', ' ')}
          </span>
          <span
            style={{
              backgroundColor: '#334155',
              color: '#94a3b8',
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '11px',
            }}
          >
            Rule: {finding.rule_id}
          </span>
          <span
            style={{
              backgroundColor: '#334155',
              color: '#cbd5e1',
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '11px',
            }}
          >
            Strength: {finding.strength}
          </span>
        </div>
        <span
          style={{
            backgroundColor: statusBadge.bg,
            color: statusBadge.text,
            border: `1px solid ${statusBadge.border}`,
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: '600',
          }}
        >
          {statusBadge.label}
        </span>
      </div>

      <h4 style={{ margin: '0 0 6px 0', fontSize: '15px', color: '#f1f5f9' }}>{finding.title}</h4>
      <p style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#cbd5e1', lineHeight: '1.4' }}>
        {finding.explanation}
      </p>

      {/* Reviewer details if already reviewed */}
      {finding.reviewer?.decision && (
        <div style={{ marginBottom: '10px', padding: '6px 10px', backgroundColor: '#0f172a', borderRadius: '4px', fontSize: '12px', color: '#94a3b8' }}>
          <strong>Decision:</strong> {finding.reviewer.decision} | <strong>By:</strong> {finding.reviewer.by || 'Unknown'} | <strong>At:</strong> {finding.reviewer.at?.slice(0, 19)}
          {finding.reviewer.reason && <div><strong>Reason:</strong> {finding.reviewer.reason}</div>}
        </div>
      )}

      {/* Human Review Actions */}
      {onReview && (
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: '#94a3b8', marginRight: '4px' }}>Reviewer Action:</span>
          <button
            disabled={submitting}
            onClick={() => handleAction('confirm', 'Confirmed by human reviewer')}
            style={{
              backgroundColor: '#166534',
              color: '#bbf7d0',
              border: '1px solid #22c55e',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: '600',
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            Confirm Observation
          </button>
          <button
            disabled={submitting}
            onClick={() => setShowDismissModal(true)}
            style={{
              backgroundColor: '#475569',
              color: '#f1f5f9',
              border: '1px solid #64748b',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: '600',
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            Dismiss (Reason Req.)
          </button>
          <button
            disabled={submitting}
            onClick={() => handleAction('escalate', 'Escalated for senior review')}
            style={{
              backgroundColor: '#854d0e',
              color: '#fef08a',
              border: '1px solid #eab308',
              borderRadius: '4px',
              padding: '4px 10px',
              fontSize: '11px',
              fontWeight: '600',
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            Escalate
          </button>
        </div>
      )}

      {/* Dismiss Modal */}
      {showDismissModal && (
        <div style={{ marginBottom: '12px', padding: '10px', backgroundColor: '#0f172a', border: '1px solid #ef4444', borderRadius: '6px' }}>
          <div style={{ fontSize: '12px', color: '#fca5a5', marginBottom: '6px', fontWeight: '600' }}>
            Provide required justification to dismiss this advisory finding:
          </div>
          <input
            type="text"
            placeholder="e.g. Authorized payroll revision letter verified on file"
            value={dismissReason}
            onChange={(e) => setDismissReason(e.target.value)}
            style={{
              width: '100%',
              padding: '6px 8px',
              backgroundColor: '#1e293b',
              border: '1px solid #475569',
              borderRadius: '4px',
              color: '#fff',
              fontSize: '12px',
              marginBottom: '8px',
              boxSizing: 'border-box',
            }}
          />
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button
              onClick={() => setShowDismissModal(false)}
              style={{ backgroundColor: 'transparent', color: '#94a3b8', border: 'none', cursor: 'pointer', fontSize: '11px' }}
            >
              Cancel
            </button>
            <button
              disabled={!dismissReason.trim() || submitting}
              onClick={() => handleAction('dismiss', dismissReason)}
              style={{
                backgroundColor: '#dc2626',
                color: '#fff',
                border: 'none',
                borderRadius: '4px',
                padding: '4px 10px',
                fontSize: '11px',
                fontWeight: '600',
                cursor: !dismissReason.trim() || submitting ? 'not-allowed' : 'pointer',
                opacity: !dismissReason.trim() ? 0.5 : 1,
              }}
            >
              Confirm Dismissal
            </button>
          </div>
        </div>
      )}

      <div style={{ borderTop: '1px solid #334155', paddingTop: '8px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '12px', color: '#94a3b8', display: 'flex', alignItems: 'center' }}>
          Evidence ({finding.evidence.length} location{finding.evidence.length > 1 ? 's' : ''}):
        </span>
        {finding.evidence.map((ev, idx) => (
          <button
            key={idx}
            onClick={() => onSelectEvidence && onSelectEvidence(idx)}
            style={{
              backgroundColor: '#0f172a',
              border: '1px solid #475569',
              borderRadius: '4px',
              color: '#38bdf8',
              padding: '3px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
          >
            {ev.doc_id} (Page {ev.page}) [{ev.bbox.join(', ')}]
          </button>
        ))}
      </div>
    </div>
  );
};
