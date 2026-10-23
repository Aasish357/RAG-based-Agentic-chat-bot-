import React, { useState } from 'react';
import { BrainIcon, PlusIcon, MessageSquareIcon, FolderIcon } from '../icons/Icons';
import DocumentManager from './DocumentManager';

export default function Sidebar({
  sessions = [],
  currentSessionId,
  onSelectSession,
  onNewChat,
  documents = [],
  onUploadDocument,
  onDeleteDocument,
  isUploading = false,
  health,
}) {
  const [activeTab, setActiveTab] = useState('chats'); // 'chats' | 'docs'
  const isOnline = health?.ollama;

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-badge">
          <div className="logo-icon">J</div>
          <span>Jahiv</span>
        </div>
      </div>

      <button className="new-chat-btn" onClick={onNewChat}>
        <PlusIcon size={16} />
        <span>New Conversation</span>
      </button>

      <div className="sidebar-nav">
        <button
          className={`nav-tab-btn ${activeTab === 'chats' ? 'active' : ''}`}
          onClick={() => setActiveTab('chats')}
        >
          <MessageSquareIcon size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Chats ({sessions.length})
        </button>
        <button
          className={`nav-tab-btn ${activeTab === 'docs' ? 'active' : ''}`}
          onClick={() => setActiveTab('docs')}
        >
          <FolderIcon size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />
          Knowledge ({documents.length})
        </button>
      </div>

      <div className="sidebar-content">
        {activeTab === 'chats' ? (
          <div>
            {sessions.length === 0 ? (
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center', marginTop: 20 }}>
                No past conversations.
              </p>
            ) : (
              sessions.map((s) => (
                <div
                  key={s.session_id}
                  className={`session-item ${s.session_id === currentSessionId ? 'active' : ''}`}
                  onClick={() => onSelectSession(s.session_id)}
                >
                  <span className="session-title">
                    {s.title || 'Conversation'}
                  </span>
                </div>
              ))
            )}
          </div>
        ) : (
          <DocumentManager
            documents={documents}
            onUpload={onUploadDocument}
            onDelete={onDeleteDocument}
            isUploading={isUploading}
          />
        )}
      </div>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <span className={`status-dot ${isOnline ? 'online' : 'offline'}`} />
          <span>{isOnline ? 'Ollama Online' : 'Ollama Offline'}</span>
        </div>
        <span>v1.0 Local</span>
      </div>
    </aside>
  );
}
