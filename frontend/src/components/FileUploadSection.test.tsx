import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import FileUploadSection from './FileUploadSection';
import * as api from '@/lib/api';

function selectFile(input: HTMLElement, file: File) {
  return userEvent.upload(input, file);
}

describe('FileUploadSection', () => {
  it('renders the uploaded file after a successful upload', async () => {
    vi.spyOn(api, 'uploadFiles').mockResolvedValue([
      {
        session_id: 'abc-123',
        category: 'property_document',
        original_filename: 'deed.pdf',
        stored_filename: 'deed.pdf',
        path: '/data/uploads/abc-123/property_document/deed.pdf',
        size_bytes: 2048,
      },
    ]);
    const onSessionId = vi.fn();

    render(
      <FileUploadSection
        title="Property Documents"
        description="desc"
        category="property_document"
        accept=".pdf"
        sessionId={null}
        onSessionId={onSessionId}
      />
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['content'], 'deed.pdf', { type: 'application/pdf' });
    await selectFile(fileInput, file);

    expect(await screen.findByText(/deed\.pdf/)).toBeInTheDocument();
    expect(onSessionId).toHaveBeenCalledWith('abc-123');
  });

  it('shows an error message when the upload fails', async () => {
    vi.spyOn(api, 'uploadFiles').mockRejectedValue(new Error('File type not allowed'));

    render(
      <FileUploadSection
        title="Property Documents"
        description="desc"
        category="property_document"
        accept=".pdf"
        sessionId={null}
        onSessionId={vi.fn()}
      />
    );

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['content'], 'oversized.pdf', { type: 'application/pdf' });
    await selectFile(fileInput, file);

    await waitFor(() => {
      expect(screen.getByText('File type not allowed')).toBeInTheDocument();
    });
  });

  it('renders the optional label when optional is set', () => {
    render(
      <FileUploadSection
        title="Supporting Images"
        description="desc"
        category="supporting_image"
        accept=".jpg"
        sessionId={null}
        onSessionId={vi.fn()}
        optional
      />
    );

    expect(screen.getByText('(optional)')).toBeInTheDocument();
  });
});
