'use client';

import { useState } from 'react';
import {
  generateReportFromSession,
  getReportDownloadUrl,
  getReportPreview,
  GenerateReportResult,
} from '@/lib/api';

interface GenerateReportSectionProps {
  sessionId: string;
}

export default function GenerateReportSection({ sessionId }: GenerateReportSectionProps) {
  const [result, setResult] = useState<GenerateReportResult | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  async function handleGenerate() {
    setError(null);
    setResult(null);
    setPreview(null);
    setIsGenerating(true);
    try {
      const generated = await generateReportFromSession(sessionId);
      setResult(generated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Report generation failed.');
    } finally {
      setIsGenerating(false);
    }
  }

  async function handlePreview() {
    if (!result) {
      return;
    }
    try {
      setPreview(await getReportPreview(result.report_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview.');
    }
  }

  return (
    <section className="card">
      <h2>Generate Report</h2>
      <p className="upload-description">
        Parses the uploaded property documents, runs AI extraction, and populates the uploaded
        template.
      </p>
      <button className="btn btn-primary" onClick={handleGenerate} disabled={isGenerating}>
        {isGenerating ? 'Generating…' : 'Generate Report'}
      </button>

      {error && <p className="upload-error">{error}</p>}

      {result && (
        <div>
          <p className={`upload-status${result.quality_check.passed ? ' status-success' : ''}`}>
            Quality check: {result.quality_check.passed ? 'Passed' : 'Issues found'}
          </p>
          {result.quality_check.injection_failures.length > 0 && (
            <p className="upload-error">
              Fields with values but no template location:{' '}
              {result.quality_check.injection_failures.join(', ')}
            </p>
          )}
          <div className="upload-status" style={{ display: 'flex', gap: '0.6rem', marginTop: '1rem' }}>
            <button className="btn btn-secondary" onClick={handlePreview}>
              Preview
            </button>
            <a className="btn btn-secondary" href={getReportDownloadUrl(result.report_id)}>
              Download .docx
            </a>
          </div>
          {preview && <pre className="report-preview">{preview}</pre>}
        </div>
      )}
    </section>
  );
}
