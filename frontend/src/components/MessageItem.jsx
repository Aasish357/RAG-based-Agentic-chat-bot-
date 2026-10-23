import React from 'react';
import AgentInspector from './AgentInspector';

export default function MessageItem({ message }) {
  const isUser = message.role === 'user';

  // Highlight citations such as [report.pdf p.3] or [report.pdf]
  const renderFormattedContent = (content) => {
    if (!content) return null;
    const citationRegex = /(\[[^\]]+\.pdf(?:\s*p\.\d+)?\]|\[[a-zA-Z0-9_\-\.\s]+\])/g;
    const parts = content.split(citationRegex);

    return parts.map((part, i) => {
      if (citationRegex.test(part)) {
        return (
          <span key={i} className="citation-tag" title="Grounding source reference">
            {part}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-avatar">
        {isUser ? 'U' : 'J'}
      </div>

      <div className="message-body">
        <div className="message-header">
          <span className="sender-name">
            {isUser ? 'You' : 'Jahiv Assistant'}
          </span>
          <span className="message-time">
            {message.timestamp || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        <div className="message-bubble">
          {renderFormattedContent(message.content)}
        </div>

        {!isUser && (message.debug || message.plan || message.critic) && (
          <AgentInspector
            debug={message.debug}
            plan={message.plan}
            critic={message.critic}
          />
        )}
      </div>
    </div>
  );
}
