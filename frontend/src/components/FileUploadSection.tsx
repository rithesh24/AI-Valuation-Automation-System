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
  onFilesUploaded?: (files: UploadedFileInfo[]) => void;
  optional?: boolean;
}

export default function FileUploadSection({
  title,
  description,
  category,
  accept,
  sessionId,
  onSessionId,
  onFilesUploaded,
  optional = false,
}: FileUploadSectionProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFileInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  async function processFiles(files: File[]) {
    if (files.length === 0) {
      return;
    }

    setError(null);
    setIsUploading(true);
    try {
      const result = await uploadFiles(files, category, sessionId);
      setUploadedFiles((previous) => [...previous, ...result]);
      onSessionId(result[0].session_id);
      onFilesUploaded?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setIsUploading(false);
    }
  }

  function handleFilesSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files;
    void processFiles(selected ? Array.from(selected) : []);
    event.target.value = '';
  }

  function handleDrop(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    void processFiles(Array.from(event.dataTransfer.files));
  }

  return (
    <section className="card">
      <h2>
        {title}
        {optional && <span className="upload-optional"> (optional)</span>}
      </h2>
      <p className="upload-description">{description}</p>

      <label
        className={`dropzone${isDragging ? ' is-dragging' : ''}`}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <span className="dropzone-icon" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 16V4M12 4l-4 4M12 4l4 4" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        <p className="dropzone-title">Drag &amp; drop files here, or click to browse</p>
        <p className="dropzone-hint">{accept.split(',').join(' · ')}</p>
        <input
          type="file"
          multiple
          accept={accept}
          onChange={handleFilesSelected}
          disabled={isUploading}
        />
      </label>

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
