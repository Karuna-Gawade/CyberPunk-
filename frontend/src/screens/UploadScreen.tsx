import React, { useState } from 'react';
import {
  createInvestigation,
  uploadDocuments,
  processInvestigation,
  getStoredLlmApiKey,
  setStoredLlmApiKey,
} from '../api/client';
import { Investigation } from '../types';

interface UploadScreenProps {
  activeInvestigation?: Investigation | null;
  onInvestigationReady: (inv: Investigation) => void;
  onViewDocument?: (docId: string) => void;
}

export const UploadScreen: React.FC<UploadScreenProps> = ({
  activeInvestigation,
  onInvestigationReady,
  onViewDocument,
}) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [statusText, setStatusText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [llmKey, setLlmKey] = useState<string>(() => getStoredLlmApiKey());
  const [showKeyInput, setShowKeyInput] = useState<boolean>(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleSaveApiKey = (key: string) => {
    setLlmKey(key);
    setStoredLlmApiKey(key);
  };

  const handleUploadAndProcess = async (createBrandNew: boolean = false) => {
    if (selectedFiles.length === 0) return;
    setLoading(true);

    try {
      let targetInvId = activeInvestigation?.investigation_id;

      if (!targetInvId || createBrandNew) {
        setStatusText('Creating new investigation ledger...');
        const newInv = await createInvestigation();
        targetInvId = newInv.investigation_id;
      }

      setStatusText(`Uploading ${selectedFiles.length} document(s)...`);
      await uploadDocuments(targetInvId, selectedFiles);

      setStatusText('Running multi-stage classification (XGBoost + LLM) and forensic rules...');
      const processedInv = await processInvestigation(targetInvId);

      setStatusText('Processing complete. All documents saved and persistent.');
      setSelectedFiles([]);
      onInvestigationReady(processedInv);
    } catch (err: any) {
      setStatusText(`Error: ${err.message || 'Operation failed'}`);
    } finally {
      setLoading(false);
    }
  };

  const savedDocs = activeInvestigation?.documents || [];

  return (
    <div style={{ maxWidth: '820px', margin: '24px auto', padding: '0 20px' }}>
      {/* Upload Main Panel */}
      <div
        className="panel"
        style={{
          padding: '24px 28px',
          backgroundColor: 'var(--bg-panel)',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px', marginBottom: '8px' }}>
          <div>
            <h2 style={{ margin: '0 0 4px 0', fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>
              Upload Document Bundle for Forensic Analysis
            </h2>
            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
              Documents are automatically saved to SQLite and persist across page refreshes.
            </p>
          </div>

          {/* LLM Engine Indicator / Toggle */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span
              style={{
                fontSize: '11px',
                fontFamily: 'var(--font-mono)',
                padding: '3px 8px',
                borderRadius: '4px',
                backgroundColor: llmKey ? '#065f46' : 'var(--bg-subtle)',
                color: llmKey ? '#6ee7b7' : 'var(--text-muted)',
                border: '1px solid var(--border-color)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>{llmKey ? '● Cloud LLM (Gemini)' : '○ Local Semantic LLM'}</span>
            </span>
            <button
              onClick={() => setShowKeyInput(!showKeyInput)}
              className="btn-action"
              style={{ fontSize: '11px', padding: '3px 8px' }}
            >
              {showKeyInput ? 'Hide Settings' : 'Configure LLM Key'}
            </button>
          </div>
        </div>

        {/* Optional LLM API Key Configuration */}
        {showKeyInput && (
          <div
            className="panel"
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--bg-subtle)',
              marginBottom: '16px',
              fontSize: '12px',
              border: '1px solid var(--border-color)',
            }}
          >
            <div style={{ fontWeight: '600', marginBottom: '4px', color: 'var(--text-main)' }}>
              Configure LLM API Key (Optional)
            </div>
            <p style={{ margin: '0 0 8px 0', color: 'var(--text-muted)', fontSize: '11px' }}>
              If left empty, the system uses the 100% offline <strong>Local Semantic Neural LLM Engine</strong>.
              Enter a Google Gemini or Groq API key to use live cloud models.
            </p>
            <div style={{ display: 'flex', gap: '8px' }}>
              <input
                type="password"
                placeholder="Enter GEMINI_API_KEY or GROQ_API_KEY"
                value={llmKey}
                onChange={(e) => handleSaveApiKey(e.target.value)}
                style={{
                  flex: 1,
                  padding: '5px 10px',
                  backgroundColor: 'var(--bg-panel)',
                  color: 'var(--text-main)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '11px',
                }}
              />
              {llmKey && (
                <button
                  onClick={() => handleSaveApiKey('')}
                  className="btn-action"
                  style={{ fontSize: '11px' }}
                >
                  Clear Key
                </button>
              )}
            </div>
          </div>
        )}

        {/* Drop Zone */}
        <div
          style={{
            border: '2px dashed var(--border-color)',
            borderRadius: '4px',
            padding: '32px 20px',
            textAlign: 'center',
            backgroundColor: 'var(--bg-subtle)',
            cursor: 'pointer',
            marginBottom: '16px',
          }}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <input
            id="file-input"
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.xls,.tiff,.bmp,.webp"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <div style={{ color: 'var(--accent-main)', fontSize: '13px', fontWeight: '700', marginBottom: '4px' }}>
            {selectedFiles.length > 0
              ? `${selectedFiles.length} file(s) selected (Click to change)`
              : 'Click to select documents to upload'}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
            PDF, DOCX, XLSX, PNG, JPG, TIFF, WebP &bull; 150 DPI render & extraction pipeline
          </div>
        </div>

        {/* Selected files preview */}
        {selectedFiles.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '11.5px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Selected for Ingestion ({selectedFiles.length}):
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {selectedFiles.map((f, i) => (
                <div
                  key={i}
                  className="panel"
                  style={{
                    backgroundColor: 'var(--bg-subtle)',
                    padding: '6px 10px',
                    fontSize: '11.5px',
                    color: 'var(--text-main)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  <span>{f.name}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{(f.size / 1024).toFixed(1)} KB</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
          <span style={{ fontSize: '12px', color: 'var(--accent-main)', fontFamily: 'var(--font-mono)' }}>
            {statusText}
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            {activeInvestigation && selectedFiles.length > 0 && (
              <button
                onClick={() => handleUploadAndProcess(false)}
                disabled={loading}
                className="btn-action btn-accent"
                style={{ padding: '6px 14px', fontSize: '12px' }}
              >
                {loading ? 'Processing...' : 'Add to Current Bundle'}
              </button>
            )}
            <button
              onClick={() => handleUploadAndProcess(true)}
              disabled={loading || selectedFiles.length === 0}
              className="btn-action"
              style={{
                padding: '6px 14px',
                fontSize: '12px',
                backgroundColor: !activeInvestigation ? 'var(--accent-main)' : undefined,
                color: !activeInvestigation ? '#ffffff' : undefined,
              }}
            >
              {loading ? 'Processing...' : activeInvestigation ? 'Start New Bundle' : 'Ingest & Classify with LLM'}
            </button>
          </div>
        </div>
      </div>

      {/* Saved Documents in Current Investigation (Persists Across Refresh) */}
      {savedDocs.length > 0 && (
        <div
          className="panel"
          style={{
            padding: '20px 24px',
            backgroundColor: 'var(--bg-panel)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div>
              <h3 style={{ margin: '0 0 2px 0', fontSize: '14px', fontWeight: '700', color: 'var(--text-main)' }}>
                Saved Documents in Active Investigation ({savedDocs.length})
              </h3>
              <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Investigation ID: {activeInvestigation?.investigation_id} &bull; Persists across browser refreshes
              </p>
            </div>
            <span
              style={{
                fontSize: '11px',
                padding: '2px 8px',
                borderRadius: '4px',
                backgroundColor: '#064e3b',
                color: '#6ee7b7',
                fontFamily: 'var(--font-mono)',
                fontWeight: '700',
              }}
            >
              Persisted in Database
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {savedDocs.map((doc) => {
              const displayType = (doc.llm_type || doc.type).toUpperCase().replace('_', ' ');
              const accuracy = doc.llm_accuracy ?? doc.type_confidence;
              const provider = doc.llm_provider || 'Local Semantic Engine';

              return (
                <div
                  key={doc.doc_id}
                  className="panel"
                  style={{
                    padding: '10px 14px',
                    backgroundColor: 'var(--bg-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '10px',
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: '700', fontSize: '12.5px', color: 'var(--text-main)' }}>
                        {doc.filename}
                      </span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: '700',
                          padding: '1px 6px',
                          borderRadius: '3px',
                          backgroundColor: '#0369a1',
                          color: '#ffffff',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {displayType}
                      </span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: '700',
                          padding: '1px 6px',
                          borderRadius: '3px',
                          backgroundColor: '#065f46',
                          color: '#6ee7b7',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {(accuracy * 100).toFixed(1)}% Accuracy
                      </span>
                    </div>

                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      SHA-256: {doc.sha256.slice(0, 16)}... &bull; {doc.pages} Page(s) &bull; Classifier: {provider}
                    </div>

                    {doc.llm_reasoning && (
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                        <span style={{ fontWeight: '600', color: 'var(--text-main)' }}>Rationale: </span>
                        {doc.llm_reasoning}
                      </div>
                    )}
                  </div>

                  {onViewDocument && (
                    <button
                      onClick={() => onViewDocument(doc.doc_id)}
                      className="btn-action"
                      style={{ fontSize: '11px', padding: '4px 10px' }}
                    >
                      Inspect in Viewer &rarr;
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
