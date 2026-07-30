'use client';

import { useState } from 'react';
import { lookupEasr, EASRGuidelineResult, EASRSearchInput } from '@/lib/api';

interface EasrLookupSectionProps {
  onResult: (tier1OfficialData: string | null) => void;
}

const CURRENT_YEAR = new Date().getFullYear();
const DEFAULT_YEAR = `${CURRENT_YEAR}-${CURRENT_YEAR + 1}`;

function formatForPrompt(result: EASRGuidelineResult): string {
  const header = `Year: ${result.search_input.year} · District: ${result.search_input.district} · Taluka: ${
    result.search_input.taluka ?? result.search_input.district_option ?? '—'
  } · Village: ${result.search_input.village}${
    result.search_input.survey_no ? ` · Survey No./SubZone: ${result.search_input.survey_no}` : ''
  }`;
  const preambleLines = Object.entries(result.preamble).map(([k, v]) => `${k}: ${v}`);
  const table = [result.columns.join(' | '), ...result.rows.map((row) => result.columns.map((c) => row[c] ?? '—').join(' | '))];
  const noteLine = result.note ? `\nNote: ${result.note}` : '';
  return [header, ...preambleLines, '', ...table, '', `Source: ${result.source}`, noteLine]
    .filter(Boolean)
    .join('\n');
}

export default function EasrLookupSection({ onResult }: EasrLookupSectionProps) {
  const [year, setYear] = useState(DEFAULT_YEAR);
  const [district, setDistrict] = useState('');
  const [districtOption, setDistrictOption] = useState('');
  const [taluka, setTaluka] = useState('');
  const [village, setVillage] = useState('');
  const [surveyNo, setSurveyNo] = useState('');
  const [result, setResult] = useState<EASRGuidelineResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [applied, setApplied] = useState(false);

  async function handleLookup() {
    setError(null);
    setResult(null);
    setApplied(false);
    setIsLoading(true);
    try {
      const searchInput: EASRSearchInput = {
        year,
        district,
        village,
        taluka: taluka || null,
        district_option: districtOption || null,
        survey_no: surveyNo || null,
      };
      const lookupResult = await lookupEasr(searchInput);
      setResult(lookupResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'eASR lookup failed.');
    } finally {
      setIsLoading(false);
    }
  }

  function handleUseThisData() {
    if (!result) return;
    onResult(formatForPrompt(result));
    setApplied(true);
  }

  function handleClear() {
    setResult(null);
    setApplied(false);
    onResult(null);
  }

  return (
    <section className="card">
      <h2>Official Guideline Rate (eASR, optional)</h2>
      <p className="upload-description">
        Look up the Maharashtra Ready Reckoner rate for the property from IGR&apos;s eASR portal.
        This grounds the AI&apos;s valuation in official government data — skip it and the report
        will note that no Tier 1 official data was available.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.6rem' }}>
        <input placeholder="Year (e.g. 2025-2026)" value={year} onChange={(e) => setYear(e.target.value)} />
        <input placeholder="District (e.g. Pune, Bombaymains)" value={district} onChange={(e) => setDistrict(e.target.value)} />
        <input
          placeholder="Sub-district (Mumbai only)"
          value={districtOption}
          onChange={(e) => setDistrictOption(e.target.value)}
        />
        <input placeholder="Taluka" value={taluka} onChange={(e) => setTaluka(e.target.value)} />
        <input placeholder="Village" value={village} onChange={(e) => setVillage(e.target.value)} />
        <input
          placeholder="Survey No./SubZone (optional)"
          value={surveyNo}
          onChange={(e) => setSurveyNo(e.target.value)}
        />
      </div>

      <button
        className="btn btn-secondary"
        onClick={handleLookup}
        disabled={isLoading || !district || !village}
        style={{ marginTop: '0.75rem' }}
      >
        {isLoading ? 'Looking up…' : 'Look Up Rate'}
      </button>

      {error && <p className="upload-error">{error}</p>}

      {result && (
        <div style={{ marginTop: '1rem' }}>
          <p className={`upload-status${result.found ? ' status-success' : ''}`}>
            {result.found ? `Found ${result.rows.length} row(s).` : 'No matching rows found.'}
          </p>
          {result.found && (
            <pre className="report-preview">{formatForPrompt(result)}</pre>
          )}
          {result.found && !applied && (
            <button className="btn btn-primary" onClick={handleUseThisData}>
              Use This Data
            </button>
          )}
          {applied && (
            <p className="upload-status status-success">
              ✓ Applied — this will be included as Tier 1 official data when generating the report.{' '}
              <button className="btn btn-secondary" onClick={handleClear} style={{ marginLeft: '0.5rem' }}>
                Clear
              </button>
            </p>
          )}
        </div>
      )}
    </section>
  );
}
