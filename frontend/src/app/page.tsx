'use client';

import { useState } from 'react';
import FileUploadSection from '@/components/FileUploadSection';

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  return (
    <main>
      <h1>AVAS</h1>
      <p>AI Valuation Automation System</p>

      <FileUploadSection
        title="Property Documents"
        description="Sale deed, title documents, approved plan, tax bill, and other property-related files (PDF, DOCX, or images)."
        category="property_document"
        accept=".pdf,.docx,.jpg,.jpeg,.png"
        sessionId={sessionId}
        onSessionId={setSessionId}
      />

      <FileUploadSection
        title="Bank Valuation Template"
        description="The bank's prescribed report template (.docx)."
        category="template"
        accept=".docx"
        sessionId={sessionId}
        onSessionId={setSessionId}
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
    </main>
  );
}
