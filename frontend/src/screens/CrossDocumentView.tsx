import React, { useState, useEffect } from 'react';
import { CrossDocComparisonField, BBox } from '../types';
import { API_BASE } from '../api/client';

interface CrossDocumentViewProps {
  investigationId: string;
  onJumpToEvidence?: (docId: string, page: number, bbox: BBox) => void;
}

export const CrossDocumentView: React.FC<CrossDocumentViewProps> = ({
  investigationId,
  onJumpToEvidence,
}) => {
  const [matrix, setMatrix] = useState<CrossDocComparisonField[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    if (!investigationId) return;
    setLoading(true);
    fetch(`${API_BASE}/investigations/${investigationId}/comparison`)
      .then((res) => res.json())
      .then((data) => setMatrix(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [investigationId]);

  if (loading) {
    return <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>Loading cross-document matrix...</div>;
  }

  if (matrix.length === 0) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>
        No cross-document correlation data available. Please upload a bundle containing multiple identity/financial documents.
      </div>
    );
  }

  const getStatusBadge = (status: string, score?: number | null) => {
    switch (status) {
      case 'match':
        return (
          <span style={{ backgroundColor: '#064e3b', color: '#34d399', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '700' }}>
            MATCH {score !== undefined && score !== null ? `(${score}%)` : ''}
          </span>
        );
      case 'needs_review':
        return (
          <span style={{ backgroundColor: '#451a03', color: '#fbbf24', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '700' }}>
            NEEDS REVIEW {score !== undefined && score !== null ? `(${score}%)` : ''}
          </span>
        );
      case 'conflict':
      default:
        return (
          <span style={{ backgroundColor: '#450a0a', color: '#f87171', padding: '2px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: '700' }}>
            CONFLICT {score !== undefined && score !== null ? `(${score}%)` : ''}
          </span>
        );
    }
  };

  return (
    <div style={{ maxWidth: '1100px', margin: '20px auto' }}>
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)', margin: '0 0 4px 0' }}>Cross-Document Correlation Matrix</h2>
        <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0, fontFamily: 'var(--font-mono)' }}>
          Multi-document verification of shared identity and financial entities across official document pairs.
        </p>
      </div>

      <div className="panel" style={{ overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
          <thead>
            <tr style={{ backgroundColor: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '8px 14px', fontWeight: '700' }}>Entity / Field</th>
              <th style={{ padding: '8px 14px', width: '150px', fontWeight: '700' }}>Correlation Status</th>
              <th style={{ padding: '8px 14px', fontWeight: '700' }}>Document 1 Comparison</th>
              <th style={{ padding: '8px 14px', fontWeight: '700' }}>Document 2 Comparison</th>
              <th style={{ padding: '8px 14px', width: '110px', fontWeight: '700' }}>Evidence Link</th>
            </tr>
          </thead>
          <tbody style={{ fontFamily: 'var(--font-mono)', fontSize: '11.5px' }}>
            {matrix.map((row, idx) => {
              const doc1 = row.docs[0];
              const doc2 = row.docs[1];

              return (
                <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  <td style={{ padding: '8px 14px', fontWeight: '600', color: 'var(--text-main)', fontFamily: 'var(--font-sans)' }}>{row.field_name}</td>
                  <td style={{ padding: '8px 14px' }}>{getStatusBadge(row.status, row.score)}</td>
                  <td style={{ padding: '8px 14px', color: 'var(--text-main)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{doc1?.doc_type}</div>
                    <div style={{ fontWeight: '500' }}>{doc1?.value}</div>
                  </td>
                  <td style={{ padding: '8px 14px', color: 'var(--text-main)' }}>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{doc2?.doc_type}</div>
                    <div style={{ fontWeight: '500' }}>{doc2?.value}</div>
                  </td>
                  <td style={{ padding: '8px 14px' }}>
                    {doc1?.bbox && onJumpToEvidence && (
                      <button
                        onClick={() => onJumpToEvidence(doc1.doc_id, doc1.page || 1, doc1.bbox!)}
                        className="btn-action"
                        style={{ fontSize: '10.5px', padding: '2px 8px' }}
                      >
                        Inspect &rarr;
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
