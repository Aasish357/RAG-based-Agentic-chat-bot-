import React, { useEffect, useRef, useState } from 'react';
import MessageItem from './MessageItem';
import { SendIcon, SparklesIcon } from '../icons/Icons';

export default function ChatWindow({
  messages = [],
  onSendMessage,
  isLoading = false,
  agentPhase = null, // 'planning' | 'tools' | 'executing' | 'critic'
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, agentPhase]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || isLoading) return;
    onSendMessage(text);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextareaInput = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`;
  };

  const suggestedQueries = [
    'Summarize the uploaded document',
    'What are the key facts and figures mentioned?',
    'Calculate the total values or percentages in the text',
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, height: 'calc(100% - 58px)', position: 'relative' }}>
      <div className="chat-scroll-area">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="chat-empty-icon">🧠</div>
            <h2>Jahiv Local Agentic RAG</h2>
            <p>
              Your 100% private, local multi-agent assistant. Powered by Ollama with Planner, Executor, and Critic agents.
            </p>

            <div className="suggested-chips">
              {suggestedQueries.map((q, idx) => (
                <button
                  key={idx}
                  className="suggested-chip"
                  onClick={() => onSendMessage(q)}
                >
                  <SparklesIcon size={14} style={{ marginRight: 6, verticalAlign: 'middle', color: 'var(--accent-purple)' }} />
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <MessageItem key={index} message={msg} />
          ))
        )}

        {isLoading && (
          <div className="pipeline-stepper">
            <div className="step-pill done">
              <span>●</span>
              <span>Input Processed</span>
            </div>
            <div style={{ color: 'var(--text-muted)' }}>→</div>
            <div className="step-pill active">
              <span>⚡</span>
              <span>Multi-Agent Pipeline Active (Planner → Tools → Executor → Critic)</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-bar">
        <form onSubmit={handleSubmit} className="input-box-wrapper">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            rows={1}
            placeholder="Ask Jahiv a question, query your documents, or calculate..."
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="send-button"
            disabled={isLoading || !input.trim()}
            title="Send query"
          >
            <SendIcon size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}
