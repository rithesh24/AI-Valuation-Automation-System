'use client';

import { useState } from 'react';
import { uploadFiles, UploadCategory, UploadedFileInfo } from '@/lib/api';

interface FileUploadSectionProps {
  title: string;
  description: string;
  category: UploadCategory;
  accept: string;
  sessionId: string | null;
  onSessionId: (sessionId: string) => void;
  optional?: boolean;
}

export default function FileUploadSection({
  title,
  description,
  category,
  accept,
  sessionId,
  onSessionId,
  optional = false,
}: FileUploadSectionProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  async function handleFilesSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files;
    if (!selected || selected.length === 0) {
      return;
    }

    setError(null);
    setIsUploading(true);
    try {
      const result = await uploadFiles(Array.from(selected), category, sessionId);
      setUploadedFiles((previous) => [...previous, ...result]);
      onSessionId(result[0].session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setIsUploading(false);
      event.target.value = '';
    }
  }

  return (
    <section className="upload-section">
      <h2>
        {title}
        {optional && <span className="upload-optional"> (optional)</span>}
      </h2>
      <p className="upload-description">{description}</p>
      <input type="file" multiple accept={accept} onChange={handleFilesSelected} disabled={isUploading} />
      {isUploading && <p className="upload-status">Uploading…</p>}
      {error && <p className="upload-error">{error}</p>}
      {uploadedFiles.length > 0 && (
        <ul className="upload-list">
          {uploadedFiles.map((file) => (
            <li key={`${file.category}-${file.stored_filename}`}>
              {file.original_filename} ({(file.size_bytes / 1024).toFixed(1)} KB)
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
