import React from 'react';
import { BrainIcon, TrashIcon, SparklesIcon } from '../icons/Icons';

export default function Header({
  health,
  onClearChat,
  criticEnabled = true,
  documentCount = 0,
}) {
  const isOnline = health?.ollama;
  const models = health?.models || [];
  const activeModel = models.length > 0 ? models[0] : 'llama3.1';

  return (
    <header className="top-header">
      <div className="header-badges">
        <div className="badge model">
          <SparklesIcon size={14} style={{ marginRight: 5, verticalAlign: 'middle' }} />
          Model: {activeModel}
        </div>

        <div className={`badge ${criticEnabled ? 'critic-on' : 'critic-off'}`}>
          Critic Agent: {criticEnabled ? 'Active' : 'Disabled'}
        </div>

        <div className="badge">
          Docs: {documentCount}
        </div>
      </div>

      <div className="header-actions">
        <button
          className="icon-btn"
          onClick={onClearChat}
          title="Clear current conversation"
        >
          <TrashIcon size={14} />
          <span>Clear Chat</span>
        </button>
      </div>
    </header>
  );
}
