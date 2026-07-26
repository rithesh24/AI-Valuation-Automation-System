import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import GenerateReportSection from './GenerateReportSection';
import * as api from '@/lib/api';

describe('GenerateReportSection', () => {
  it('shows the quality check result and a download link after generating', async () => {
    vi.spyOn(api, 'generateReportFromSession').mockResolvedValue({
      report_id: 'report-1',
      injection: { output_path: '/tmp/report.docx', filled_fields: ['a'], unmapped_fields: [] },
      quality_check: { passed: true, injection_failures: [], disclosed_unavailable: [] },
    });

    render(<GenerateReportSection sessionId="session-1" />);
    await userEvent.click(screen.getByRole('button', { name: 'Generate Report' }));

    expect(await screen.findByText(/Quality check: Passed/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Download .docx' })).toHaveAttribute(
      'href',
      expect.stringContaining('/reports/report-1/download')
    );
  });

  it('shows injection failures when the quality check does not pass', async () => {
    vi.spyOn(api, 'generateReportFromSession').mockResolvedValue({
      report_id: 'report-1',
      injection: { output_path: '/tmp/report.docx', filled_fields: [], unmapped_fields: [] },
      quality_check: {
        passed: false,
        injection_failures: ['property_identification.district'],
        disclosed_unavailable: [],
      },
    });

    render(<GenerateReportSection sessionId="session-1" />);
    await userEvent.click(screen.getByRole('button', { name: 'Generate Report' }));

    expect(await screen.findByText(/Quality check: Issues found/)).toBeInTheDocument();
    expect(screen.getByText(/property_identification.district/)).toBeInTheDocument();
  });

  it('shows an error message when generation fails', async () => {
    vi.spyOn(api, 'generateReportFromSession').mockRejectedValue(
      new Error('No property documents uploaded')
    );

    render(<GenerateReportSection sessionId="session-1" />);
    await userEvent.click(screen.getByRole('button', { name: 'Generate Report' }));

    expect(await screen.findByText('No property documents uploaded')).toBeInTheDocument();
  });

  it('loads and displays the preview text on demand', async () => {
    vi.spyOn(api, 'generateReportFromSession').mockResolvedValue({
      report_id: 'report-1',
      injection: { output_path: '/tmp/report.docx', filled_fields: [], unmapped_fields: [] },
      quality_check: { passed: true, injection_failures: [], disclosed_unavailable: [] },
    });
    vi.spyOn(api, 'getReportPreview').mockResolvedValue('VALUATION REPORT\nDistrict: Pune');

    render(<GenerateReportSection sessionId="session-1" />);
    await userEvent.click(screen.getByRole('button', { name: 'Generate Report' }));
    await screen.findByText(/Quality check: Passed/);
    await userEvent.click(screen.getByRole('button', { name: 'Preview' }));

    expect(await screen.findByText(/District: Pune/)).toBeInTheDocument();
  });
});
