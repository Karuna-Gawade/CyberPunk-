import React, { useState } from 'react';
import { createInvestigation, uploadDocuments, processInvestigation } from '../api/client';
import { Investigation } from '../types';

interface UploadScreenProps {
  onInvestigationReady: (inv: Investigation) => void;
}

export const UploadScreen: React.FC<UploadScreenProps> = ({ onInvestigationReady }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [statusText, setStatusText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleUploadAndProcess = async () => {
    if (selectedFiles.length === 0) return;
    setLoading(true);
    setStatusText('Creating investigation ledger...');

    try {
      const inv = await createInvestigation();
      setStatusText(`Uploading ${selectedFiles.length} document(s)...`);

      await uploadDocuments(inv.investigation_id, selectedFiles);
      setStatusText('Classifying and extracting document structures at 150 DPI...');

      const processedInv = await processInvestigation(inv.investigation_id);
      setStatusText('Processing complete.');
      onInvestigationReady(processedInv);
    } catch (err: any) {
      setStatusText(`Error: ${err.message || 'Operation failed'}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '780px', margin: '30px auto', padding: '0 20px' }}>
      <div
        className="panel"
        style={{
          padding: '28px',
          backgroundColor: 'var(--bg-panel)',
        }}
      >
        <h2 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: '700', color: 'var(--text-main)' }}>
          Upload Document Bundle for Forensic Analysis
        </h2>
        <p style={{ margin: '0 0 20px 0', fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: '1.45' }}>
          Select or drop synthetic Indian financial and identity documents (Aadhaar, PAN, Salary Slip, Bank Statement in PDF or image format).
          Originals are secured read-only; documents are classified and processed deterministically.
        </p>

        <div
          style={{
            border: '2px dashed var(--border-color)',
            borderRadius: '4px',
            padding: '36px',
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
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={handleFileChange}
            style={{ display: 'none' }}
          />
          <div style={{ color: 'var(--accent-main)', fontSize: '13px', fontWeight: '700', marginBottom: '4px' }}>
            {selectedFiles.length > 0
              ? `${selectedFiles.length} file(s) selected`
              : 'Click to select documents from your computer'}
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
            Supported formats: PDF (vector & scanned), PNG, JPG (150 DPI render pipeline)
          </div>
        </div>

        {selectedFiles.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '12px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Selected Files:</h4>
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

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '12px', color: 'var(--accent-main)', fontFamily: 'var(--font-mono)' }}>{statusText}</span>
          <button
            onClick={handleUploadAndProcess}
            disabled={loading || selectedFiles.length === 0}
            className="btn-action btn-accent"
            style={{
              padding: '6px 16px',
              fontSize: '12px',
            }}
          >
            {loading ? 'Processing Bundle...' : 'Ingest & Analyze Bundle'}
          </button>
        </div>
      </div>
    </div>
  );
};
