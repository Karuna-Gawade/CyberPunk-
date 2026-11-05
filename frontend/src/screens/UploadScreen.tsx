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
    <div style={{ maxWidth: '800px', margin: '40px auto', padding: '0 20px' }}>
      <div
        style={{
          backgroundColor: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '8px',
          padding: '32px',
        }}
      >
        <h2 style={{ margin: '0 0 12px 0', fontSize: '18px', color: '#f8fafc' }}>
          Upload Document Bundle for Forensic Analysis
        </h2>
        <p style={{ margin: '0 0 24px 0', fontSize: '13px', color: '#94a3b8', lineHeight: '1.5' }}>
          Select or drop synthetic Indian financial and identity documents (Aadhaar, PAN, Salary Slip, Bank Statement in PDF or image format).
          Originals are secured read-only; documents are classified and processed deterministically.
        </p>

        <div
          style={{
            border: '2px dashed #475569',
            borderRadius: '8px',
            padding: '40px',
            textAlign: 'center',
            backgroundColor: '#0f172a',
            cursor: 'pointer',
            marginBottom: '20px',
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
          <div style={{ color: '#38bdf8', fontSize: '14px', fontWeight: '600', marginBottom: '6px' }}>
            {selectedFiles.length > 0
              ? `${selectedFiles.length} file(s) selected`
              : 'Click to select documents from your computer'}
          </div>
          <div style={{ color: '#64748b', fontSize: '12px' }}>
            Supported formats: PDF (vector & scanned), PNG, JPG (150 DPI render pipeline)
          </div>
        </div>

        {selectedFiles.length > 0 && (
          <div style={{ marginBottom: '20px' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '13px', color: '#cbd5e1' }}>Selected Files:</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {selectedFiles.map((f, i) => (
                <div
                  key={i}
                  style={{
                    backgroundColor: '#0f172a',
                    padding: '8px 12px',
                    borderRadius: '4px',
                    fontSize: '12px',
                    color: '#94a3b8',
                    display: 'flex',
                    justifyContent: 'space-between',
                  }}
                >
                  <span>{f.name}</span>
                  <span>{(f.size / 1024).toFixed(1)} KB</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '13px', color: '#38bdf8' }}>{statusText}</span>
          <button
            onClick={handleUploadAndProcess}
            disabled={loading || selectedFiles.length === 0}
            style={{
              backgroundColor: loading || selectedFiles.length === 0 ? '#334155' : '#0284c7',
              color: '#ffffff',
              border: 'none',
              padding: '10px 24px',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: loading || selectedFiles.length === 0 ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Processing Bundle...' : 'Ingest & Analyze Bundle'}
          </button>
        </div>
      </div>
    </div>
  );
};
