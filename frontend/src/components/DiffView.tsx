import React from 'react';
import type { FileDiff, Finding, Hunk } from '../types';
import FindingCard from './FindingCard';

interface DiffViewProps {
  diff: FileDiff;
  findings: Finding[];
}

export default function DiffView({ diff, findings }: DiffViewProps) {
  // Group findings by line number for easy access during rendering
  const findingsByLine = findings.reduce((acc, finding) => {
    // We attach the finding to the end_line of the finding range
    const line = finding.line_end;
    if (!acc[line]) acc[line] = [];
    acc[line].push(finding);
    return acc;
  }, {} as Record<number, Finding[]>);

  const renderHunk = (hunk: Hunk, hunkIndex: number) => {
    let currentOldLine = hunk.old_start;
    let currentNewLine = hunk.new_start;
    const elements: React.ReactNode[] = [];

    // Hunk header
    elements.push(
      <div key={`header-${hunkIndex}`} className="flex font-mono text-xs text-text-muted bg-[#1c2128] py-1 border-b border-[#30363d]">
        <div className="w-12 flex-none border-r border-[#30363d]"></div>
        <div className="w-12 flex-none border-r border-[#30363d]"></div>
        <div className="px-4 flex-1 whitespace-pre">{hunk.header}</div>
      </div>
    );

    hunk.lines.forEach((line, lineIndex) => {
      const isAdd = line.startsWith('+');
      const isDel = line.startsWith('-');
      
      const oldLineNum = isAdd ? '' : currentOldLine++;
      const newLineNum = isDel ? '' : currentNewLine++;
      
      const lineFindings = (newLineNum !== '' && findingsByLine[newLineNum as number]) || [];
      
      let bgClass = 'bg-transparent hover:bg-surface-overlay';
      let textClass = 'text-text-primary';
      
      if (isAdd) {
        bgClass = 'bg-[rgba(46,160,67,0.15)] hover:bg-[rgba(46,160,67,0.25)]';
      } else if (isDel) {
        bgClass = 'bg-[rgba(248,81,73,0.15)] hover:bg-[rgba(248,81,73,0.25)]';
      }

      elements.push(
        <div key={`line-${hunkIndex}-${lineIndex}`} className={`flex font-mono text-xs ${bgClass}`}>
          <div className="w-12 flex-none text-right px-2 py-0.5 text-text-muted select-none border-r border-[#30363d]">
            {oldLineNum}
          </div>
          <div className="w-12 flex-none text-right px-2 py-0.5 text-text-muted select-none border-r border-[#30363d]">
            {newLineNum}
          </div>
          <div className={`px-4 py-0.5 flex-1 whitespace-pre-wrap break-all ${textClass}`}>
            {line}
          </div>
        </div>
      );

      // Render findings right below the line they belong to
      if (lineFindings.length > 0) {
        elements.push(
          <div key={`finding-${hunkIndex}-${lineIndex}`} className="flex border-b border-[#30363d]">
            <div className="w-24 flex-none bg-surface-raised border-r border-[#30363d]"></div>
            <div className="flex-1 p-4 bg-surface-raised">
              {lineFindings.map((finding, fi) => (
                <FindingCard key={`f-${fi}`} finding={finding} />
              ))}
            </div>
          </div>
        );
      }
    });

    return elements;
  };

  return (
    <div className="border border-[#30363d] rounded-md overflow-hidden bg-surface">
      <div className="px-4 py-3 bg-surface-raised border-b border-[#30363d] flex items-center">
        <span className="font-mono text-sm font-medium text-text-primary">
          {diff.filename}
        </span>
        {diff.is_new && <span className="ml-3 px-1.5 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded border border-[rgba(46,160,67,0.4)] text-[rgba(46,160,67,1)]">Added</span>}
        {diff.is_deleted && <span className="ml-3 px-1.5 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded border border-[rgba(248,81,73,0.4)] text-[rgba(248,81,73,1)]">Deleted</span>}
      </div>
      <div className="flex flex-col">
        {diff.hunks.map((hunk, i) => renderHunk(hunk, i))}
      </div>
    </div>
  );
}
