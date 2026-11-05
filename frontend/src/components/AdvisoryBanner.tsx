import React from 'react';

export const AdvisoryBanner: React.FC = () => {
  return (
    <div
      style={{
        backgroundColor: '#0F172A',
        color: '#F8FAFC',
        padding: '6px 16px',
        fontWeight: '600',
        fontSize: '11px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid var(--border-color)',
        letterSpacing: '0.02em',
        fontFamily: 'var(--font-mono)',
        userSelect: 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ color: '#F59E0B', fontWeight: 'bold' }}>[ADVISORY NOTICE]</span>
        <span>Advisory output. Final decision rests with the human reviewer.</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: '#94A3B8' }}>
        <span>ISO/IEC 27037 ALIGNED</span>
        <span>•</span>
        <span style={{ color: '#34D399', fontWeight: '600' }}>SHA-256 AUDIT LEDGER</span>
      </div>
    </div>
  );
};
