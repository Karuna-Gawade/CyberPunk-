import React from 'react';

export const AdvisoryBanner: React.FC = () => {
  return (
    <div
      style={{
        backgroundColor: '#f59e0b',
        color: '#78350f',
        padding: '10px 16px',
        fontWeight: '700',
        fontSize: '13px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '8px',
        borderBottom: '2px solid #d97706',
        letterSpacing: '0.02em',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      }}
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
      <span>Advisory output. Final decision rests with the human reviewer.</span>
    </div>
  );
};
