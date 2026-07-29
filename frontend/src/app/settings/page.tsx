'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getApiKeyStatus, setApiKey } from '@/lib/api';

export default function Settings() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [savedJustNow, setSavedJustNow] = useState(false);

  useEffect(() => {
    getApiKeyStatus()
      .then((status) => setConfigured(status.configured))
      .catch((err) => setError(err.message));
  }, []);

  async function handleSave() {
    setError(null);
    setSavedJustNow(false);
    setIsSaving(true);
    try {
      const status = await setApiKey(apiKeyInput);
      setConfigured(status.configured);
      setApiKeyInput('');
      setSavedJustNow(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save API key.');
    } finally {
      setIsSaving(false);
    }
  }

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
        <span className="badge">Settings</span>
        <h1>
          <span className="gradient-text">Claude</span> API Key
        </h1>
      </section>

      <section className="card">
        <div className="card-header">
          <span className="card-icon" aria-hidden="true">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 7a4 4 0 11-8 0 4 4 0 018 0zM11 11l-7 7v3h3l7-7m-3-3l3 3m2-9l3 3-3 3"
              />
            </svg>
          </span>
          <div>
            <h2>Anthropic API Key</h2>
            <p className="upload-description">
              Required for AI extraction and report generation. Your key is saved on this
              computer only and is never sent anywhere except Anthropic.
            </p>
          </div>
        </div>

        {configured !== null && (
          <span className={`status-pill${configured ? ' status-pill-active' : ''}`}>
            <span className="status-dot" aria-hidden="true" />
            {configured ? 'Key configured' : 'No key configured yet'}
          </span>
        )}

        <input
          type="password"
          className="text-input"
          placeholder="sk-ant-..."
          value={apiKeyInput}
          onChange={(event) => setApiKeyInput(event.target.value)}
          disabled={isSaving}
        />
        <button
          className="btn btn-primary"
          onClick={handleSave}
          disabled={isSaving || !apiKeyInput.trim()}
        >
          {isSaving ? 'Saving…' : 'Save Key'}
        </button>

        {savedJustNow && <p className="upload-status status-success">Saved.</p>}
        {error && <p className="upload-error">{error}</p>}
      </section>
    </main>
  );
}
