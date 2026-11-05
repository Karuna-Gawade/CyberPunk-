import React, { useState, useEffect } from 'react';
import { CrossDocComparisonField, BBox } from '../types';

const API_BASE = 'http://localhost:8000';

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
      <div style={{ marginBottom: '20px' }}>
        <h2 style={{ fontSize: '18px', color: '#f8fafc', margin: '0 0 6px 0' }}>Cross-Document Correlation Matrix</h2>
        <p style={{ fontSize: '13px', color: '#94a3b8', margin: 0 }}>
          Multi-document verification of shared identity and financial entities across official document pairs.
        </p>
      </div>

      <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
          <thead>
            <tr style={{ backgroundColor: '#0f172a', borderBottom: '1px solid #334155', color: '#94a3b8' }}>
              <th style={{ padding: '12px 16px' }}>Entity / Field</th>
              <th style={{ padding: '12px 16px', width: '150px' }}>Correlation Status</th>
              <th style={{ padding: '12px 16px' }}>Document 1 Comparison</th>
              <th style={{ padding: '12px 16px' }}>Document 2 Comparison</th>
              <th style={{ padding: '12px 16px', width: '120px' }}>Evidence Link</th>
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, idx) => {
              const doc1 = row.docs[0];
              const doc2 = row.docs[1];

              return (
                <tr key={idx} style={{ borderBottom: '1px solid #334155' }}>
                  <td style={{ padding: '12px 16px', fontWeight: '600', color: '#f8fafc' }}>{row.field_name}</td>
                  <td style={{ padding: '12px 16px' }}>{getStatusBadge(row.status, row.score)}</td>
                  <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>
                    <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase' }}>{doc1?.doc_type}</div>
                    <div style={{ fontWeight: '500' }}>{doc1?.value}</div>
                  </td>
                  <td style={{ padding: '12px 16px', color: '#cbd5e1' }}>
                    <div style={{ fontSize: '11px', color: '#64748b', textTransform: 'uppercase' }}>{doc2?.doc_type}</div>
                    <div style={{ fontWeight: '500' }}>{doc2?.value}</div>
                  </td>
                  <td style={{ padding: '12px 16px' }}>
                    {doc1?.bbox && onJumpToEvidence && (
                      <button
                        onClick={() => onJumpToEvidence(doc1.doc_id, doc1.page || 1, doc1.bbox!)}
                        style={{
                          backgroundColor: '#0f172a',
                          border: '1px solid #0284c7',
                          color: '#38bdf8',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          cursor: 'pointer',
                        }}
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
