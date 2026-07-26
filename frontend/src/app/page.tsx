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
      <h1>AVAS</h1>
      <p>AI Valuation Automation System</p>
      <p className="upload-description">
        <Link href="/dashboard">View usage dashboard &rarr;</Link>
      </p>

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
