import React, { useRef, useState } from 'react';
import { UploadIcon, FileTextIcon, TrashIcon } from '../icons/Icons';

export default function DocumentManager({
  documents = [],
  onUpload,
  onDelete,
  isUploading = false,
}) {
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file && file.name.toLowerCase().endsWith('.pdf')) {
      onUpload(file);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file && file.name.toLowerCase().endsWith('.pdf')) {
      onUpload(file);
    }
  };

  return (
    <div className="doc-panel">
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".pdf"
        style={{ display: 'none' }}
      />

      <div
        className={`upload-dropzone ${dragOver ? 'drag-over' : ''}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        <UploadIcon size={24} style={{ color: 'var(--accent-purple)', marginBottom: 8 }} />
        <p style={{ fontWeight: 600, fontSize: '0.88rem', marginBottom: 4 }}>
          {isUploading ? 'Chunking & Embedding...' : 'Upload Knowledge PDF'}
        </p>
        <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Click or drag & drop (Max 50MB)
        </p>
      </div>

      <div style={{ marginTop: 8 }}>
        <p style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 8 }}>
          Indexed Documents ({documents.length})
        </p>

        {documents.length === 0 ? (
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
            No documents indexed. Upload a PDF to empower the RAG retriever.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {documents.map((doc, idx) => (
              <div key={doc.document_id || idx} className="doc-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FileTextIcon size={18} style={{ color: 'var(--accent-cyan)' }} />
                  <div className="doc-info">
                    <span className="doc-name" title={doc.filename}>{doc.filename}</span>
                    <span className="doc-meta">
                      {doc.pages ? `${doc.pages} pages • ` : ''}
                      {doc.chunks_count || doc.chunks_indexed || 0} chunks
                    </span>
                  </div>
                </div>

                <button
                  className="del-btn"
                  title="Remove document"
                  onClick={() => onDelete(doc.document_id)}
                >
                  <TrashIcon size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
