'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getMonthlyUsage, MonthlyUsage } from '@/lib/api';

export default function Dashboard() {
  const [usage, setUsage] = useState<MonthlyUsage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMonthlyUsage()
      .then(setUsage)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <main>
      <header className="page-header">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"
              />
            </svg>
          </span>
          AVAS
        </div>
        <Link href="/" className="nav-link">
          &larr; Back to upload
        </Link>
      </header>

      <section className="hero">
        <span className="badge">Usage</span>
        <h1>
          <span className="gradient-text">Dashboard</span>
        </h1>
      </section>

      {error && <p className="upload-error">{error}</p>}

      {!error && !usage && <p className="upload-status">Loading...</p>}

      {usage && (
        <>
          <p className="upload-description">
            {new Date(usage.year, usage.month - 1).toLocaleString('en-US', {
              month: 'long',
              year: 'numeric',
            })}
          </p>
          <div className="stat-grid">
            <div className="stat-tile">
              <span className="stat-label">Requests</span>
              <span className="stat-value">{usage.request_count}</span>
            </div>
            <div className="stat-tile">
              <span className="stat-label">Input Tokens</span>
              <span className="stat-value">{usage.input_tokens.toLocaleString()}</span>
            </div>
            <div className="stat-tile">
              <span className="stat-label">Output Tokens</span>
              <span className="stat-value">{usage.output_tokens.toLocaleString()}</span>
            </div>
            <div className="stat-tile">
              <span className="stat-label">Total Tokens</span>
              <span className="stat-value">{usage.total_tokens.toLocaleString()}</span>
            </div>
            <div className="stat-tile">
              <span className="stat-label">Estimated Cost</span>
              <span className="stat-value">${usage.cost_usd.toFixed(2)}</span>
            </div>
          </div>
        </>
      )}
    </main>
  );
}
