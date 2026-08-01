const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export type UploadCategory = 'property_document' | 'template' | 'supporting_image';

export interface UploadedFileInfo {
  session_id: string;
  category: UploadCategory;
  original_filename: string;
  stored_filename: string;
  path: string;
  size_bytes: number;
}

export async function uploadFiles(
  files: File[],
  category: UploadCategory,
  sessionId: string | null
): Promise<UploadedFileInfo[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  formData.append('category', category);
  if (sessionId) {
    formData.append('session_id', sessionId);
  }

  const response = await fetch(`${API_BASE_URL}/uploads`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Upload failed with status ${response.status}`);
  }

  return response.json();
}

export interface MonthlyUsage {
  year: number;
  month: number;
  request_count: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
}

export async function getMonthlyUsage(): Promise<MonthlyUsage> {
  const response = await fetch(`${API_BASE_URL}/usage/monthly`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Failed to load usage with status ${response.status}`);
  }

  return response.json();
}

export interface InjectionResult {
  output_path: string;
  filled_fields: string[];
  unmapped_fields: string[];
}

export interface QualityCheckResult {
  passed: boolean;
  injection_failures: string[];
  disclosed_unavailable: string[];
}

export interface OfficialRateCitation {
  source: string;
  rate: string;
  unit: string;
  access_date: string;
  remarks: string;
}

export interface GenerateReportResult {
  report_id: string;
  injection: InjectionResult;
  quality_check: QualityCheckResult;
  extracted_data: {
    official_rate_evidence: OfficialRateCitation[];
  };
}

export async function generateReportFromSession(
  sessionId: string,
  tier1OfficialData?: string | null
): Promise<GenerateReportResult> {
  const response = await fetch(`${API_BASE_URL}/reports/generate-from-session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      ...(tier1OfficialData ? { tier1_official_data: tier1OfficialData } : {}),
    }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Report generation failed with status ${response.status}`);
  }

  return response.json();
}

export interface EASRSearchInput {
  year: string;
  district: string;
  taluka?: string | null;
  village: string;
  district_option?: string | null;
  survey_no?: string | null;
}

export interface EASRGuidelineResult {
  search_input: EASRSearchInput;
  found: boolean;
  columns: string[];
  rows: Record<string, string | null>[];
  preamble: Record<string, string>;
  source: string;
  accessed_at: string;
  note?: string | null;
}

export async function lookupEasr(searchInput: EASRSearchInput): Promise<EASRGuidelineResult> {
  const response = await fetch(`${API_BASE_URL}/easr/lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(searchInput),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `eASR lookup failed with status ${response.status}`);
  }

  return response.json();
}

export async function getReportPreview(reportId: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/reports/${reportId}/preview`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Failed to load preview with status ${response.status}`);
  }

  const body = await response.json();
  return body.text;
}

export function getReportDownloadUrl(reportId: string): string {
  return `${API_BASE_URL}/reports/${reportId}/download`;
}

export interface GenerationProgress {
  percent: number;
  stage: string;
}

export async function getReportProgress(sessionId: string): Promise<GenerationProgress> {
  const response = await fetch(`${API_BASE_URL}/reports/progress/${sessionId}`);

  if (!response.ok) {
    throw new Error(`Failed to load progress with status ${response.status}`);
  }

  return response.json();
}

export interface ApiKeyStatus {
  configured: boolean;
}

export async function getApiKeyStatus(): Promise<ApiKeyStatus> {
  const response = await fetch(`${API_BASE_URL}/settings/api-key`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Failed to load settings with status ${response.status}`);
  }

  return response.json();
}

export async function setApiKey(apiKey: string): Promise<ApiKeyStatus> {
  const response = await fetch(`${API_BASE_URL}/settings/api-key`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Failed to save API key with status ${response.status}`);
  }

  return response.json();
}
