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
      <h1>Usage Dashboard</h1>
      <p className="upload-description">
        <Link href="/">&larr; Back to upload</Link>
      </p>

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
