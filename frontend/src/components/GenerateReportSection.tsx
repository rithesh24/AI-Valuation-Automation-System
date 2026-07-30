'use client';

import { useRef, useState, type CSSProperties } from 'react';
import {
  generateReportFromSession,
  getReportDownloadUrl,
  getReportPreview,
  getReportProgress,
  GenerateReportResult,
  GenerationProgress,
} from '@/lib/api';

interface GenerateReportSectionProps {
  sessionId: string;
  tier1OfficialData?: string | null;
}

const POLL_INTERVAL_MS = 800;

export default function GenerateReportSection({ sessionId, tier1OfficialData }: GenerateReportSectionProps) {
  const [result, setResult] = useState<GenerateReportResult | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState<GenerationProgress>({ percent: 0, stage: '' });
  const pollHandle = useRef<ReturnType<typeof setInterval> | null>(null);

  async function handleGenerate() {
    setError(null);
    setResult(null);
    setPreview(null);
    setProgress({ percent: 0, stage: 'Starting…' });
    setIsGenerating(true);

    pollHandle.current = setInterval(async () => {
      try {
        setProgress(await getReportProgress(sessionId));
      } catch {
        // transient poll failure — next tick will retry
      }
    }, POLL_INTERVAL_MS);

    try {
      const generated = await generateReportFromSession(sessionId, tier1OfficialData);
      setResult(generated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Report generation failed.');
    } finally {
      if (pollHandle.current) {
        clearInterval(pollHandle.current);
        pollHandle.current = null;
      }
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

      {isGenerating && (
        <div className="progress-ring-wrap">
          <div
            className="progress-donut"
            role="progressbar"
            aria-valuenow={progress.percent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Report generation progress"
            style={{ '--percent': progress.percent } as CSSProperties}
          >
            <span>{progress.percent}%</span>
          </div>
          <p className="upload-status">{progress.stage || 'Starting…'}</p>
        </div>
      )}

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
