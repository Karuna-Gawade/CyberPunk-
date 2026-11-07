import React, { useState, useEffect } from 'react';
import { AdvisoryBanner } from './components/AdvisoryBanner';
import { UploadScreen } from './screens/UploadScreen';
import { DocumentView } from './screens/DocumentView';
import { CrossDocumentView } from './screens/CrossDocumentView';
import { FindingsView } from './screens/FindingsView';
import { InvestigationAnalyticsView } from './screens/InvestigationAnalyticsView';
import { Investigation, CapabilitiesReport, BBox } from './types';
import { getCapabilities, getInvestigation, listInvestigations } from './api/client';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<'upload' | 'document' | 'cross_doc' | 'findings' | 'analytics' | 'capabilities'>(() => {
    return (localStorage.getItem('active_tab') as any) || 'upload';
  });
  const [activeInvestigation, setActiveInvestigation] = useState<Investigation | null>(null);
  const [allInvestigations, setAllInvestigations] = useState<Investigation[]>([]);
  const [activeDocId, setActiveDocId] = useState<string>(() => localStorage.getItem('active_doc_id') || '');
  const [activePage, setActivePage] = useState<number>(1);
  const [highlightBBox, setHighlightBBox] = useState<BBox | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilitiesReport | null>(null);

  // Visual-only Theme Selection
  const [theme, setTheme] = useState<string>(() => localStorage.getItem('agy_theme') || 'bluewhite');

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('theme-casefile', 'theme-institutional', 'theme-controlroom');
    if (theme === 'casefile') root.classList.add('theme-casefile');
    else if (theme === 'institutional') root.classList.add('theme-institutional');
    else if (theme === 'controlroom') root.classList.add('theme-controlroom');
    localStorage.setItem('agy_theme', theme);
  }, [theme]);

  useEffect(() => {
    getCapabilities()
      .then((data) => setCapabilities(data))
      .catch((err) => console.error(err));
  }, []);

  // Restore saved investigation on browser refresh
  useEffect(() => {
    const savedInvId = localStorage.getItem('active_investigation_id');
    const savedDocId = localStorage.getItem('active_doc_id');

    if (savedInvId) {
      getInvestigation(savedInvId)
        .then((inv) => {
          setActiveInvestigation(inv);
          if (inv.documents.length > 0) {
            const hasDoc = inv.documents.some((d) => d.doc_id === savedDocId);
            setActiveDocId(hasDoc && savedDocId ? savedDocId : inv.documents[0].doc_id);
          }
        })
        .catch(() => {
          // If saved inv missing, fetch latest available
          listInvestigations().then((invs) => {
            if (invs && invs.length > 0) {
              const latest = invs[0];
              setActiveInvestigation(latest);
              localStorage.setItem('active_investigation_id', latest.investigation_id);
              if (latest.documents.length > 0) setActiveDocId(latest.documents[0].doc_id);
            }
          });
        });
    } else {
      listInvestigations().then((invs) => {
        if (invs && invs.length > 0) {
          const latest = invs[0];
          setActiveInvestigation(latest);
          localStorage.setItem('active_investigation_id', latest.investigation_id);
          if (latest.documents.length > 0) setActiveDocId(latest.documents[0].doc_id);
        }
      });
    }
  }, []);

  // Keep all investigations list updated
  useEffect(() => {
    listInvestigations()
      .then((invs) => setAllInvestigations(invs || []))
      .catch(() => {});
  }, [activeInvestigation]);

  // Persist active states
  useEffect(() => {
    if (activeInvestigation) {
      localStorage.setItem('active_investigation_id', activeInvestigation.investigation_id);
    }
  }, [activeInvestigation]);

  useEffect(() => {
    localStorage.setItem('active_tab', currentTab);
  }, [currentTab]);

  useEffect(() => {
    if (activeDocId) {
      localStorage.setItem('active_doc_id', activeDocId);
    }
  }, [activeDocId]);

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
        className="panel"
        style={{
          borderLeft: 'none',
          borderRight: 'none',
          borderTop: 'none',
          padding: '10px 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '15px', fontWeight: '700', color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
              AI Document Forensics & Contextual Intelligence
            </h1>
            <p style={{ margin: '2px 0 0 0', fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              PS-2 &bull; Multi-Stage Classification (XGBoost + LLM) &bull; Persistent Forensic Ledger
            </p>
          </div>

          {/* Investigation Switcher / Creator */}
          {allInvestigations.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
              <select
                value={activeInvestigation?.investigation_id || ''}
                onChange={(e) => {
                  const match = allInvestigations.find((inv) => inv.investigation_id === e.target.value);
                  if (match) {
                    setActiveInvestigation(match);
                    if (match.documents.length > 0) setActiveDocId(match.documents[0].doc_id);
                  }
                }}
                style={{
                  fontSize: '11px',
                  padding: '3px 8px',
                  backgroundColor: 'var(--bg-subtle)',
                  color: 'var(--text-main)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                  fontFamily: 'var(--font-mono)',
                  maxWidth: '190px',
                }}
              >
                {allInvestigations.map((inv) => (
                  <option key={inv.investigation_id} value={inv.investigation_id}>
                    {inv.investigation_id} ({inv.documents.length} doc{inv.documents.length !== 1 ? 's' : ''})
                  </option>
                ))}
              </select>

              <button
                onClick={() => {
                  setActiveInvestigation(null);
                  localStorage.removeItem('active_investigation_id');
                  setActiveDocId('');
                  setCurrentTab('upload');
                }}
                className="btn-action"
                style={{ fontSize: '11px', padding: '3px 8px' }}
                title="Start a fresh investigation bundle"
              >
                + New Bundle
              </button>
            </div>
          )}
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            onClick={() => setCurrentTab('upload')}
            className={`btn-action ${currentTab === 'upload' ? 'btn-accent' : ''}`}
          >
            Upload Bundle
          </button>
          <button
            onClick={() => setCurrentTab('findings')}
            className={`btn-action ${currentTab === 'findings' ? 'btn-accent' : ''}`}
          >
            Findings
          </button>
          <button
            onClick={() => setCurrentTab('cross_doc')}
            className={`btn-action ${currentTab === 'cross_doc' ? 'btn-accent' : ''}`}
          >
            Cross-Document
          </button>
          <button
            onClick={() => setCurrentTab('analytics')}
            className={`btn-action ${currentTab === 'analytics' ? 'btn-accent' : ''}`}
          >
            Evidence & Analytics
          </button>
          <button
            onClick={() => {
              setHighlightBBox(null);
              setCurrentTab('document');
            }}
            className={`btn-action ${currentTab === 'document' ? 'btn-accent' : ''}`}
          >
            Document View {activeInvestigation ? `(${activeInvestigation.documents.length})` : ''}
          </button>
          <button
            onClick={() => setCurrentTab('capabilities')}
            className={`btn-action ${currentTab === 'capabilities' ? 'btn-accent' : ''}`}
          >
            Capabilities
          </button>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {/* Visual-only Theme Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', border: '1px solid var(--border-color)', padding: '2px 4px', borderRadius: '4px', backgroundColor: 'var(--bg-panel)' }}>
            <span style={{ fontSize: '10px', fontWeight: 'bold', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', padding: '0 4px' }}>THEME:</span>
            <button
              onClick={() => setTheme('bluewhite')}
              className={`btn-action ${theme === 'bluewhite' ? 'btn-accent' : ''}`}
              style={{ fontSize: '10px', padding: '2px 6px', fontFamily: 'var(--font-mono)' }}
            >
              Default
            </button>
            <button
              onClick={() => setTheme('casefile')}
              className={`btn-action ${theme === 'casefile' ? 'btn-accent' : ''}`}
              style={{ fontSize: '10px', padding: '2px 6px', fontFamily: 'var(--font-mono)' }}
            >
              Case File
            </button>
            <button
              onClick={() => setTheme('institutional')}
              className={`btn-action ${theme === 'institutional' ? 'btn-accent' : ''}`}
              style={{ fontSize: '10px', padding: '2px 6px', fontFamily: 'var(--font-mono)' }}
            >
              Institutional
            </button>
            <button
              onClick={() => setTheme('controlroom')}
              className={`btn-action ${theme === 'controlroom' ? 'btn-accent' : ''}`}
              style={{ fontSize: '10px', padding: '2px 6px', fontFamily: 'var(--font-mono)' }}
            >
              Control Room
            </button>
          </div>

          <span
            style={{
              backgroundColor: 'var(--bg-subtle)',
              color: 'var(--text-muted)',
              padding: '3px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: '600',
              border: '1px solid var(--border-color)',
              fontFamily: 'var(--font-mono)',
            }}
          >
            Persistent DB
          </span>
        </div>
      </header>

      <main style={{ flex: 1, padding: '20px', maxWidth: '1400px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
        {currentTab === 'upload' && (
          <UploadScreen
            activeInvestigation={activeInvestigation}
            onInvestigationReady={handleInvestigationReady}
            onViewDocument={(docId) => {
              setActiveDocId(docId);
              setActivePage(1);
              setHighlightBBox(null);
              setCurrentTab('document');
            }}
          />
        )}

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

        {currentTab === 'analytics' && activeInvestigation && (
          <InvestigationAnalyticsView
            investigationId={activeInvestigation.investigation_id}
            documents={activeInvestigation.documents}
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
            <h2 style={{ fontSize: '16px', color: 'var(--text-main)', marginBottom: '14px', fontWeight: '700' }}>System Capabilities Status</h2>
            <div className="panel" style={{ overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12px' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '8px 14px', fontWeight: '700' }}>Feature</th>
                    <th style={{ padding: '8px 14px', width: '120px', fontWeight: '700' }}>Status</th>
                    <th style={{ padding: '8px 14px', fontWeight: '700' }}>Details</th>
                  </tr>
                </thead>
                <tbody style={{ fontFamily: 'var(--font-mono)', fontSize: '11.5px' }}>
                  {capabilities.capabilities.map((c, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '8px 14px', fontWeight: '600', color: 'var(--text-main)', fontFamily: 'var(--font-sans)' }}>{c.feature}</td>
                      <td style={{ padding: '8px 14px' }}>
                        <span
                          className={
                            c.status === 'implemented'
                              ? 'badge-obs'
                              : c.status === 'partial'
                              ? 'badge-incons'
                              : 'badge-manip'
                          }
                          style={{
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: '700',
                            textTransform: 'uppercase',
                          }}
                        >
                          {c.status}
                        </span>
                      </td>
                      <td style={{ padding: '8px 14px', color: 'var(--text-muted)', fontFamily: 'var(--font-sans)', fontSize: '12px' }}>{c.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      <footer
        className="panel"
        style={{
          borderLeft: 'none',
          borderRight: 'none',
          borderBottom: 'none',
          padding: '8px 24px',
          textAlign: 'center',
          fontSize: '11px',
          color: 'var(--text-muted)',
          fontFamily: 'var(--font-mono)',
        }}
      >
        Advisory Document Forensics &bull; Informed by ISO/IEC 27037, 27041, 27042, NIST SP 800-86
      </footer>
    </div>
  );
};

export default App;
