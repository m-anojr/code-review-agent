import { useState } from 'react';
import type { Finding } from '../types';

export default function FindingCard({ finding }: { finding: Finding }) {
  const [showFix, setShowFix] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);

  const colors = {
    critical: 'border-l-severity-critical text-severity-critical',
    high: 'border-l-severity-high text-severity-high',
    medium: 'border-l-severity-medium text-severity-medium',
    low: 'border-l-severity-low text-severity-low',
  };

  return (
    <div className={`my-2 bg-surface rounded-r-md border border-l-4 border-border shadow-sm overflow-hidden ${colors[finding.severity]}`}>
      <div className="px-4 py-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="uppercase text-xs font-bold tracking-wider">{finding.severity}</span>
          <span className="text-text-muted text-xs border border-border px-1.5 rounded">{finding.category}</span>
          <span className="ml-auto text-xs text-text-secondary">{finding.source === 'rule' ? 'Static rule' : 'AI review'}</span>
          {finding.source === 'agent' && <span className="rounded border border-border px-1.5 py-0.5 text-[10px] text-text-muted">Model confidence {Math.round(finding.confidence * 100)}%</span>}
        </div>
        <p className="mb-2 text-[11px] font-mono text-text-muted">Line {finding.line_start}{finding.line_end !== finding.line_start ? `–${finding.line_end}` : ''}</p>
        <p className="text-sm text-text-primary">{finding.explanation}</p>
        
        {finding.suggested_fix && (
          <div className="mt-3">
            <button 
              onClick={() => setShowFix(!showFix)}
              className="text-xs text-accent hover:underline focus:outline-none"
              aria-expanded={showFix}
            >
              {showFix ? 'Hide suggested fix' : 'Show suggested fix'}
            </button>
            {showFix && (
              <pre className="mt-2 p-3 bg-[#0d1117] rounded border border-border text-xs text-text-secondary overflow-x-auto whitespace-pre-wrap font-mono">
                {finding.suggested_fix}
              </pre>
            )}
          </div>
        )}
        {finding.source === 'agent' && finding.reasoning_trace && (
          <div className="mt-2">
            <button type="button" onClick={() => setShowEvidence(!showEvidence)} aria-expanded={showEvidence} className="text-xs text-text-secondary hover:text-text-primary focus:outline-none">
              {showEvidence ? 'Hide evidence summary' : 'Evidence summary'}
            </button>
            {showEvidence && <p className="mt-2 rounded border border-border bg-surface-raised p-3 text-xs leading-5 text-text-secondary">{finding.reasoning_trace}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
