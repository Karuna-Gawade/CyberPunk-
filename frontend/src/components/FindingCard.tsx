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
        return { borderLeft: 'var(--tier-manip)', badgeClass: 'badge-manip' };
      case 'inconsistency':
        return { borderLeft: 'var(--tier-incons)', badgeClass: 'badge-incons' };
      case 'observation':
      default:
        return { borderLeft: 'var(--tier-obs)', badgeClass: 'badge-obs' };
    }
  };

  const colors = getTierColor(finding.tier);

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
      className="panel"
      style={{
        borderLeft: `4px solid ${colors.borderLeft}`,
        padding: '14px',
        marginBottom: '10px',
        backgroundColor: 'var(--bg-panel)',
        color: 'var(--text-main)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span
            className={colors.badgeClass}
            style={{
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '10px',
              fontWeight: '700',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            {finding.tier.replace('_', ' ')}
          </span>
          <span
            style={{
              backgroundColor: 'var(--bg-subtle)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-color)',
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            Rule: {finding.rule_id}
          </span>
          <span
            style={{
              backgroundColor: 'var(--bg-subtle)',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-color)',
              padding: '2px 6px',
              borderRadius: '4px',
              fontSize: '11px',
              fontFamily: 'var(--font-mono)',
            }}
          >
            Strength: {finding.strength}
          </span>
        </div>
        <span
          style={{
            backgroundColor: 'var(--bg-subtle)',
            color: 'var(--text-main)',
            border: '1px solid var(--border-color)',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            fontWeight: '600',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {finding.status === 'confirmed_by_reviewer' ? 'Confirmed by Reviewer' : finding.status === 'dismissed' ? 'Dismissed' : 'Requires investigation'}
        </span>
      </div>

      <h4 style={{ margin: '0 0 6px 0', fontSize: '14px', fontWeight: '700', color: 'var(--text-main)' }}>{finding.title}</h4>
      <p style={{ margin: '0 0 10px 0', fontSize: '13px', color: 'var(--text-muted)', lineHeight: '1.45' }}>
        {finding.explanation}
      </p>

      {/* Related converging findings */}
      {finding.related_finding_ids && finding.related_finding_ids.length > 0 && (
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '10px', fontFamily: 'var(--font-mono)', padding: '4px 8px', background: 'var(--bg-subtle)', border: '1px solid var(--border-color)', borderRadius: '4px' }}>
          <strong>Related findings:</strong> {finding.related_finding_ids.join(', ')}
        </div>
      )}

      {/* Reviewer details if already reviewed */}
      {finding.reviewer?.decision && (
        <div style={{ marginBottom: '10px', padding: '6px 10px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border-color)', borderRadius: '4px', fontSize: '11.5px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          <strong>Decision:</strong> {finding.reviewer.decision} | <strong>By:</strong> {finding.reviewer.by || 'Unknown'} | <strong>At:</strong> {finding.reviewer.at?.slice(0, 19)}
          {finding.reviewer.reason && <div style={{ marginTop: '2px' }}><strong>Reason:</strong> {finding.reviewer.reason}</div>}
        </div>
      )}

      {/* Human Review Actions */}
      {onReview && (
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 'bold', textTransform: 'uppercase' }}>Reviewer Action:</span>
          <button
            disabled={submitting}
            onClick={() => handleAction('confirm', 'Confirmed by human reviewer')}
            className="btn-action"
            style={{ fontSize: '11px', padding: '3px 8px' }}
          >
            Confirm Observation
          </button>
          <button
            disabled={submitting}
            onClick={() => setShowDismissModal(true)}
            className="btn-action"
            style={{ fontSize: '11px', padding: '3px 8px' }}
          >
            Dismiss (Reason Req.)
          </button>
          <button
            disabled={submitting}
            onClick={() => handleAction('escalate', 'Escalated for senior review')}
            className="btn-action"
            style={{ fontSize: '11px', padding: '3px 8px' }}
          >
            Escalate
          </button>
        </div>
      )}

      {/* Dismiss Modal */}
      {showDismissModal && (
        <div style={{ marginBottom: '12px', padding: '10px', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--tier-manip)', borderRadius: '4px' }}>
          <div style={{ fontSize: '12px', color: 'var(--tier-manip)', marginBottom: '6px', fontWeight: '600' }}>
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
              backgroundColor: 'var(--bg-panel)',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              color: 'var(--text-main)',
              fontSize: '12px',
              marginBottom: '8px',
              boxSizing: 'border-box',
              fontFamily: 'var(--font-sans)',
            }}
          />
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
            <button
              onClick={() => setShowDismissModal(false)}
              className="btn-action"
              style={{ fontSize: '11px' }}
            >
              Cancel
            </button>
            <button
              disabled={!dismissReason.trim() || submitting}
              onClick={() => handleAction('dismiss', dismissReason)}
              className="btn-action btn-accent"
              style={{
                fontSize: '11px',
                opacity: !dismissReason.trim() ? 0.5 : 1,
              }}
            >
              Confirm Dismissal
            </button>
          </div>
        </div>
      )}

      <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '8px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', fontWeight: 'bold' }}>
          Evidence ({finding.evidence.length} location{finding.evidence.length > 1 ? 's' : ''}):
        </span>
        {finding.evidence.map((ev, idx) => (
          <button
            key={idx}
            onClick={() => onSelectEvidence && onSelectEvidence(idx)}
            className="btn-action"
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '10.5px',
              padding: '2px 6px',
            }}
          >
            {ev.doc_id} (Page {ev.page}) [{ev.bbox.join(', ')}]
          </button>
        ))}
      </div>
    </div>
  );
};
