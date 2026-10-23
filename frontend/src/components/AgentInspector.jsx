import React, { useState } from 'react';
import { ChevronDownIcon, ChevronRightIcon, CheckCircleIcon, AlertCircleIcon } from '../icons/Icons';

export default function AgentInspector({ debug, plan, critic }) {
  const [open, setOpen] = useState(false);

  // Normalize details from debug dict or individual plan/critic objects
  const toolsUsed = debug?.tools_used || plan?.tools_needed || (plan?.tool ? [plan.tool] : []);
  const retrievalQuery = debug?.retrieval_query || plan?.retrieval_query || plan?.query || 'None';
  const criticVerdict = debug?.critic_verdict || critic?.verdict || 'PASS';
  const criticIssues = debug?.critic_issues || critic?.issues || 'NONE';
  const planNotes = plan?.plan || (typeof plan === 'string' ? plan : '');

  const hasCriticPassed = criticVerdict.toUpperCase() === 'PASS';

  return (
    <div className="agent-meta-box">
      <button
        className="agent-meta-toggle"
        onClick={() => setOpen(!open)}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {hasCriticPassed ? (
            <CheckCircleIcon size={14} style={{ color: 'var(--accent-green)' }} />
          ) : (
            <AlertCircleIcon size={14} style={{ color: 'var(--accent-amber)' }} />
          )}
          <span>Agent Trace & Tool Execution</span>
        </span>
        {open ? <ChevronDownIcon size={14} /> : <ChevronRightIcon size={14} />}
      </button>

      {open && (
        <div className="agent-meta-details">
          <div className="meta-row">
            <span className="meta-label">Tools Used:</span>
            <span className="meta-value">
              {toolsUsed.length > 0 ? toolsUsed.join(', ') : 'Direct synthesis (No tools)'}
            </span>
          </div>

          <div className="meta-row">
            <span className="meta-label">Retrieval Query:</span>
            <span className="meta-value">{retrievalQuery}</span>
          </div>

          <div className="meta-row">
            <span className="meta-label">Critic Verdict:</span>
            <span
              className="meta-value"
              style={{
                color: hasCriticPassed ? 'var(--accent-green)' : 'var(--accent-amber)',
                fontWeight: 600,
              }}
            >
              {criticVerdict} {criticIssues !== 'NONE' ? `(${criticIssues})` : ''}
            </span>
          </div>

          {planNotes && (
            <div style={{ marginTop: 4 }}>
              <span className="meta-label" style={{ display: 'block', marginBottom: 2 }}>Planner Output:</span>
              <pre
                style={{
                  background: 'var(--bg-secondary)',
                  padding: '6px 8px',
                  borderRadius: 4,
                  fontSize: '0.75rem',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {planNotes}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
