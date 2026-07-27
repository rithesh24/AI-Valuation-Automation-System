'use client';

import { useState } from 'react';
import Link from 'next/link';
import FileUploadSection from '@/components/FileUploadSection';
import GenerateReportSection from '@/components/GenerateReportSection';

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [hasPropertyDocument, setHasPropertyDocument] = useState(false);
  const [hasTemplate, setHasTemplate] = useState(false);

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
        <Link href="/dashboard" className="nav-link">
          View usage dashboard &rarr;
        </Link>
      </header>

      <section className="hero">
        <span className="badge">AI Powered</span>
        <h1>
          <span className="gradient-text">Valuation</span> reports, automated
        </h1>
        <p>
          Upload property documents and your bank&apos;s template — AVAS extracts the facts,
          researches comparables, and fills the report for you.
        </p>
      </section>

      <FileUploadSection
        title="Property Documents"
        description="Sale deed, title documents, approved plan, tax bill, and other property-related files (PDF, DOCX, or images)."
        category="property_document"
        accept=".pdf,.docx,.jpg,.jpeg,.png"
        sessionId={sessionId}
        onSessionId={setSessionId}
        onFilesUploaded={() => setHasPropertyDocument(true)}
      />

      <FileUploadSection
        title="Bank Valuation Template"
        description="The bank's prescribed report template (.docx)."
        category="template"
        accept=".docx"
        sessionId={sessionId}
        onSessionId={setSessionId}
        onFilesUploaded={() => setHasTemplate(true)}
      />

      <FileUploadSection
        title="Supporting Images"
        description="Site photographs or other supporting images."
        category="supporting_image"
        accept=".jpg,.jpeg,.png"
        sessionId={sessionId}
        onSessionId={setSessionId}
        optional
      />

      {sessionId && hasTemplate && hasPropertyDocument && (
        <GenerateReportSection sessionId={sessionId} />
      )}
    </main>
  );
}
