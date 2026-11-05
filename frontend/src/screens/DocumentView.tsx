import React, { useState, useEffect } from 'react';
import { DocumentRecord, ExtractedField, BBox } from '../types';
import { getDocumentFields, getDocumentPageImageUrl, revealField } from '../api/client';

interface DocumentViewProps {
  documents: DocumentRecord[];
  activeDocId?: string;
  initialPage?: number;
  highlightBBox?: BBox | null;
  onSelectDoc?: (docId: string) => void;
}

export const DocumentView: React.FC<DocumentViewProps> = ({
  documents,
  activeDocId,
  initialPage = 1,
  highlightBBox,
  onSelectDoc,
}) => {
  const currentDocId = activeDocId || (documents[0]?.doc_id ?? '');
  const currentDoc = documents.find((d) => d.doc_id === currentDocId);

  const [currentPage, setCurrentPage] = useState<number>(initialPage);

  useEffect(() => {
    if (initialPage) {
      setCurrentPage(initialPage);
    }
  }, [initialPage, activeDocId]);
  const [fields, setFields] = useState<ExtractedField[]>([]);
  const [hoveredFieldId, setHoveredFieldId] = useState<string | null>(null);
  const [revealedValues, setRevealedValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (!currentDocId) return;
    setLoading(true);
    getDocumentFields(currentDocId)
      .then((data) => setFields(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, [currentDocId]);

  const handleReveal = async (fieldId: string) => {
    try {
      const res = await revealField(fieldId);
      setRevealedValues((prev) => ({ ...prev, [fieldId]: String(res.unmasked_value) }));
    } catch (err) {
      console.error(err);
    }
  };

  if (!currentDoc) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#94a3b8' }}>
        No document selected. Please upload and process a document bundle.
      </div>
    );
  }

  const pageFields = fields.filter((f) => f.page === currentPage);
  const imageUrl = getDocumentPageImageUrl(currentDoc.doc_id, currentPage);

  return (
    <div style={{ display: 'flex', gap: '20px', height: 'calc(100vh - 140px)' }}>
      {/* Left: Document View with BBox Overlay */}
      <div
        style={{
          flex: '1 1 65%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '8px',
          overflow: 'hidden',
        }}
      >
        {/* Document Header Controls */}
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: '#1e293b',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: '1px solid #334155',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <select
              value={currentDoc.doc_id}
              onChange={(e) => onSelectDoc && onSelectDoc(e.target.value)}
              style={{
                backgroundColor: '#0f172a',
                color: '#f8fafc',
                border: '1px solid #475569',
                padding: '6px 12px',
                borderRadius: '4px',
                fontSize: '13px',
              }}
            >
              {documents.map((d) => (
                <option key={d.doc_id} value={d.doc_id}>
                  {d.filename} ({d.type.toUpperCase()})
                </option>
              ))}
            </select>
            <span
              style={{
                fontSize: '11px',
                fontWeight: '700',
                padding: '2px 8px',
                borderRadius: '4px',
                textTransform: 'uppercase',
                backgroundColor: currentDoc.status === 'processed' ? '#064e3b' : '#7f1d1d',
                color: currentDoc.status === 'processed' ? '#34d399' : '#f87171',
              }}
            >
              {currentDoc.status}
            </span>
          </div>

          {currentDoc.pages > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                style={{
                  backgroundColor: '#334155',
                  color: '#f8fafc',
                  border: 'none',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  cursor: currentPage <= 1 ? 'not-allowed' : 'pointer',
                  opacity: currentPage <= 1 ? 0.5 : 1,
                }}
              >
                &larr; Prev
              </button>
              <span style={{ fontSize: '13px', color: '#94a3b8' }}>
                Page {currentPage} of {currentDoc.pages}
              </span>
              <button
                disabled={currentPage >= currentDoc.pages}
                onClick={() => setCurrentPage((p) => Math.min(currentDoc.pages, p + 1))}
                style={{
                  backgroundColor: '#334155',
                  color: '#f8fafc',
                  border: 'none',
                  padding: '4px 10px',
                  borderRadius: '4px',
                  cursor: currentPage >= currentDoc.pages ? 'not-allowed' : 'pointer',
                  opacity: currentPage >= currentDoc.pages ? 0.5 : 1,
                }}
              >
                Next &rarr;
              </button>
            </div>
          )}
        </div>

        {/* Rendered Document Canvas with SVG BBox Overlays */}
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '20px',
            display: 'flex',
            justifyContent: 'center',
            backgroundColor: '#020617',
          }}
        >
          <div style={{ position: 'relative', display: 'inline-block' }}>
            <img
              src={imageUrl}
              alt={`Page ${currentPage}`}
              style={{
                display: 'block',
                maxWidth: '100%',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                border: '1px solid #334155',
              }}
            />

            {/* Bounding Box Overlay SVG */}
            <svg
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                pointerEvents: 'none',
              }}
            >
              {pageFields.map((f) => {
                const isHovered = hoveredFieldId === f.field_id;
                const [x0, y0, x1, y1] = f.bbox;
                const width = Math.max(2, x1 - x0);
                const height = Math.max(2, y1 - y0);

                return (
                  <rect
                    key={f.field_id}
                    x={x0}
                    y={y0}
                    width={width}
                    height={height}
                    fill={isHovered ? 'rgba(56, 189, 248, 0.25)' : 'rgba(59, 130, 246, 0.1)'}
                    stroke={isHovered ? '#38bdf8' : '#3b82f6'}
                    strokeWidth={isHovered ? 2.5 : 1.2}
                    strokeDasharray={isHovered ? 'none' : '2,2'}
                  />
                );
              })}

              {/* Dedicated finding highlight box if present */}
              {highlightBBox && (
                <rect
                  x={highlightBBox[0]}
                  y={highlightBBox[1]}
                  width={highlightBBox[2] - highlightBBox[0]}
                  height={highlightBBox[3] - highlightBBox[1]}
                  fill="rgba(239, 68, 68, 0.25)"
                  stroke="#ef4444"
                  strokeWidth={3}
                />
              )}
            </svg>
          </div>
        </div>
      </div>

      {/* Right: Extracted Fields Sidebar */}
      <div
        style={{
          flex: '1 1 35%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#0f172a',
          border: '1px solid #1e293b',
          borderRadius: '8px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            padding: '12px 16px',
            backgroundColor: '#1e293b',
            borderBottom: '1px solid #334155',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h3 style={{ margin: 0, fontSize: '14px', color: '#f8fafc', fontWeight: '600' }}>
            Extracted Fields ({pageFields.length})
          </h3>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>DPI: 150</span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#94a3b8' }}>Loading fields...</div>
          ) : pageFields.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
              No structured fields extracted on this page.
            </div>
          ) : (
            pageFields.map((f) => {
              const displayVal = revealedValues[f.field_id] || (typeof f.value === 'object' ? JSON.stringify(f.value) : String(f.value));
              const isMasked = f.name.includes('aadhaar') || f.name.includes('pan');
              const isRevealed = Boolean(revealedValues[f.field_id]);

              return (
                <div
                  key={f.field_id}
                  onMouseEnter={() => setHoveredFieldId(f.field_id)}
                  onMouseLeave={() => setHoveredFieldId(null)}
                  style={{
                    backgroundColor: hoveredFieldId === f.field_id ? '#1e293b' : '#0f172a',
                    border: `1px solid ${hoveredFieldId === f.field_id ? '#38bdf8' : '#334155'}`,
                    borderRadius: '6px',
                    padding: '10px',
                    marginBottom: '8px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', fontWeight: '700', color: '#93c5fd', textTransform: 'uppercase' }}>
                      {f.name.replace(/_/g, ' ')}
                    </span>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          backgroundColor: '#1e293b',
                          color: '#94a3b8',
                          padding: '1px 5px',
                          borderRadius: '3px',
                          border: '1px solid #475569',
                        }}
                      >
                        {f.source}
                      </span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: '600',
                          backgroundColor: f.confidence >= 0.85 ? '#064e3b' : '#78350f',
                          color: f.confidence >= 0.85 ? '#34d399' : '#fcd34d',
                          padding: '1px 5px',
                          borderRadius: '3px',
                        }}
                      >
                        {(f.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  <div style={{ fontSize: '13px', color: '#f8fafc', wordBreak: 'break-word', marginTop: '4px' }}>
                    {f.unable_to_assess ? (
                      <span style={{ color: '#f87171', fontStyle: 'italic' }}>Unable to assess this field</span>
                    ) : (
                      displayVal
                    )}
                  </div>

                  {isMasked && !f.unable_to_assess && (
                    <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'flex-end' }}>
                      <button
                        onClick={() => handleReveal(f.field_id)}
                        disabled={isRevealed}
                        style={{
                          backgroundColor: isRevealed ? '#334155' : '#0284c7',
                          color: '#ffffff',
                          border: 'none',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          cursor: isRevealed ? 'default' : 'pointer',
                        }}
                      >
                        {isRevealed ? 'Revealed (Audited)' : 'Reveal (Audit-Logged)'}
                      </button>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
