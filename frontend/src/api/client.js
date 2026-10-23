/**
 * API client communicating with Jahiv FastAPI backend.
 */

const BASE_URL = '';

export async function checkHealth() {
  try {
    const res = await fetch(`${BASE_URL}/health`);
    if (!res.ok) throw new Error(`Health check returned status ${res.status}`);
    return await res.json();
  } catch (err) {
    return { ollama: false, models: [], error: err.message };
  }
}

export async function sendChatMessage(message, sessionId = null) {
  const payload = { message };
  if (sessionId) payload.session_id = sessionId;

  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Server error (${res.status})`);
  }

  return await res.json();
}

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed (${res.status})`);
  }

  return await res.json();
}

export async function fetchDocuments() {
  const res = await fetch(`${BASE_URL}/api/documents`);
  if (!res.ok) throw new Error(`Failed to fetch documents (${res.status})`);
  return await res.json();
}

export async function deleteDocument(docId) {
  const res = await fetch(`${BASE_URL}/api/documents/${docId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete document (${res.status})`);
  return await res.json();
}

export async function fetchSessionMemory(sessionId) {
  const res = await fetch(`${BASE_URL}/api/memory/${sessionId}`);
  if (!res.ok) throw new Error(`Failed to fetch memory (${res.status})`);
  return await res.json();
}

export async function clearConversation() {
  const res = await fetch(`${BASE_URL}/api/clear`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to clear conversation (${res.status})`);
  return await res.json();
}

export async function fetchBackendStatus() {
  const res = await fetch(`${BASE_URL}/api/status`);
  if (!res.ok) throw new Error(`Failed to fetch status (${res.status})`);
  return await res.json();
}
