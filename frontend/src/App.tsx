import React, { useState, useEffect } from 'react';
import { AdvisoryBanner } from './components/AdvisoryBanner';
import { UploadScreen } from './screens/UploadScreen';
import { DocumentView } from './screens/DocumentView';
import { CrossDocumentView } from './screens/CrossDocumentView';
import { FindingsView } from './screens/FindingsView';
import { Investigation, CapabilitiesReport, BBox } from './types';
import { getCapabilities } from './api/client';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<'upload' | 'document' | 'cross_doc' | 'findings' | 'capabilities'>('upload');
  const [activeInvestigation, setActiveInvestigation] = useState<Investigation | null>(null);
  const [activeDocId, setActiveDocId] = useState<string>('');
  const [activePage, setActivePage] = useState<number>(1);
  const [highlightBBox, setHighlightBBox] = useState<BBox | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilitiesReport | null>(null);

  useEffect(() => {
    getCapabilities()
      .then((data) => setCapabilities(data))
      .catch((err) => console.error(err));
  }, []);

  const handleInvestigationReady = (inv: Investigation) => {
    setActiveInvestigation(inv);
    if (inv.documents.length > 0) {
      setActiveDocId(inv.documents[0].doc_id);
    }
    setCurrentTab('findings');
  };

  const handleJumpToEvidence = (docId: string, page: number, bbox: BBox) => {
    setActiveDocId(docId);
    setActivePage(page);
    setHighlightBBox(bbox);
    setCurrentTab('document');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <AdvisoryBanner />

      <header
        style={{
          backgroundColor: '#0f172a',
          borderBottom: '1px solid #1e293b',
          padding: '12px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: '17px', fontWeight: '700', color: '#f8fafc' }}>
            AI Document Forensics and Contextual Intelligence System
          </h1>
          <p style={{ margin: '3px 0 0 0', fontSize: '11px', color: '#94a3b8' }}>
            PS-2 &bull; Deterministic Forensic Architecture &bull; Human-in-the-Loop
          </p>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setCurrentTab('upload')}
            style={{
              backgroundColor: currentTab === 'upload' ? '#1e293b' : 'transparent',
              color: currentTab === 'upload' ? '#38bdf8' : '#94a3b8',
              border: `1px solid ${currentTab === 'upload' ? '#38bdf8' : '#334155'}`,
              padding: '6px 14px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Upload Bundle
          </button>
          <button
            onClick={() => setCurrentTab('findings')}
            style={{
              backgroundColor: currentTab === 'findings' ? '#1e293b' : 'transparent',
              color: currentTab === 'findings' ? '#38bdf8' : '#94a3b8',
              border: `1px solid ${currentTab === 'findings' ? '#38bdf8' : '#334155'}`,
              padding: '6px 14px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Findings
          </button>
          <button
            onClick={() => setCurrentTab('cross_doc')}
            style={{
              backgroundColor: currentTab === 'cross_doc' ? '#1e293b' : 'transparent',
              color: currentTab === 'cross_doc' ? '#38bdf8' : '#94a3b8',
              border: `1px solid ${currentTab === 'cross_doc' ? '#38bdf8' : '#334155'}`,
              padding: '6px 14px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Cross-Document
          </button>
          <button
            onClick={() => {
              setHighlightBBox(null);
              setCurrentTab('document');
            }}
            style={{
              backgroundColor: currentTab === 'document' ? '#1e293b' : 'transparent',
              color: currentTab === 'document' ? '#38bdf8' : '#94a3b8',
              border: `1px solid ${currentTab === 'document' ? '#38bdf8' : '#334155'}`,
              padding: '6px 14px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Document View {activeInvestigation ? `(${activeInvestigation.documents.length})` : ''}
          </button>
          <button
            onClick={() => setCurrentTab('capabilities')}
            style={{
              backgroundColor: currentTab === 'capabilities' ? '#1e293b' : 'transparent',
              color: currentTab === 'capabilities' ? '#38bdf8' : '#94a3b8',
              border: `1px solid ${currentTab === 'capabilities' ? '#38bdf8' : '#334155'}`,
              padding: '6px 14px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Capabilities
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <span
            style={{
              backgroundColor: '#064e3b',
              color: '#34d399',
              padding: '4px 10px',
              borderRadius: '9999px',
              fontSize: '11px',
              fontWeight: '600',
              border: '1px solid #059669',
            }}
          >
            Offline Mode
          </span>
        </div>
      </header>

      <main style={{ flex: 1, padding: '20px', maxWidth: '1400px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
        {currentTab === 'upload' && <UploadScreen onInvestigationReady={handleInvestigationReady} />}

        {currentTab === 'findings' && activeInvestigation && (
          <FindingsView
            investigationId={activeInvestigation.investigation_id}
            onJumpToEvidence={handleJumpToEvidence}
          />
        )}

        {currentTab === 'cross_doc' && activeInvestigation && (
          <CrossDocumentView
            investigationId={activeInvestigation.investigation_id}
            onJumpToEvidence={handleJumpToEvidence}
          />
        )}

        {currentTab === 'document' && (
          <DocumentView
            documents={activeInvestigation?.documents || []}
            activeDocId={activeDocId}
            initialPage={activePage}
            highlightBBox={highlightBBox}
            onSelectDoc={(id) => {
              setActiveDocId(id);
              setActivePage(1);
              setHighlightBBox(null);
            }}
          />
        )}

        {currentTab === 'capabilities' && capabilities && (
          <div style={{ maxWidth: '900px', margin: '20px auto' }}>
            <h2 style={{ fontSize: '18px', color: '#f8fafc', marginBottom: '16px' }}>System Capabilities Status</h2>
            <div style={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ backgroundColor: '#0f172a', borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                    <th style={{ padding: '12px 16px' }}>Feature</th>
                    <th style={{ padding: '12px 16px', width: '130px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {capabilities.capabilities.map((c, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #334155' }}>
                      <td style={{ padding: '10px 16px', fontWeight: '600', color: '#f8fafc' }}>{c.feature}</td>
                      <td style={{ padding: '10px 16px' }}>
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: '700',
                            textTransform: 'uppercase',
                            backgroundColor:
                              c.status === 'implemented'
                                ? '#064e3b'
                                : c.status === 'partial'
                                ? '#451a03'
                                : '#374151',
                            color:
                              c.status === 'implemented'
                                ? '#34d399'
                                : c.status === 'partial'
                                ? '#fbbf24'
                                : '#9ca3af',
                          }}
                        >
                          {c.status}
                        </span>
                      </td>
                      <td style={{ padding: '10px 16px', color: '#cbd5e1' }}>{c.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      <footer
        style={{
          borderTop: '1px solid #1e293b',
          padding: '10px 24px',
          textAlign: 'center',
          fontSize: '11px',
          color: '#64748b',
          backgroundColor: '#0f172a',
        }}
      >
        Advisory Document Forensics &bull; Informed by ISO/IEC 27037, 27041, 27042, NIST SP 800-86
      </footer>
    </div>
  );
};

export default App;
