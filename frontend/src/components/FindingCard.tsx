import { useState } from 'react';
import type { Finding } from '../types';

export default function FindingCard({ finding }: { finding: Finding }) {
  const [expanded, setExpanded] = useState(false);

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
          <span className="text-text-muted text-xs ml-auto font-mono">source: {finding.source}</span>
        </div>
        <p className="text-sm text-text-primary">{finding.explanation}</p>
        
        {finding.suggested_fix && (
          <div className="mt-3">
            <button 
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-accent hover:underline focus:outline-none"
            >
              {expanded ? 'Hide suggestion' : 'Show suggested fix'}
            </button>
            {expanded && (
              <pre className="mt-2 p-3 bg-[#0d1117] rounded border border-border text-xs text-text-secondary overflow-x-auto whitespace-pre-wrap font-mono">
                {finding.suggested_fix}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
