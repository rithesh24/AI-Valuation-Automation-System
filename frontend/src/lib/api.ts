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
