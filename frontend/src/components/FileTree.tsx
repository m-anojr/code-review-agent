import type { FileDiff, Finding, Severity } from '../types';

interface FileTreeProps {
  files: FileDiff[];
  findings: Finding[];
  selected: string | null;
  onSelect: (filename: string) => void;
}

export default function FileTree({ files, findings, selected, onSelect }: FileTreeProps) {
  const getSeverityColor = (severity: Severity) => {
    switch (severity) {
      case 'critical': return 'bg-severity-critical/20 text-severity-critical border-severity-critical/30';
      case 'high': return 'bg-severity-high/20 text-severity-high border-severity-high/30';
      case 'medium': return 'bg-severity-medium/20 text-severity-medium border-severity-medium/30';
      case 'low': return 'bg-severity-low/20 text-severity-low border-severity-low/30';
    }
  };

  const getHighestSeverity = (fileFindings: Finding[]): Severity | null => {
    if (fileFindings.length === 0) return null;
    if (fileFindings.some(f => f.severity === 'critical')) return 'critical';
    if (fileFindings.some(f => f.severity === 'high')) return 'high';
    if (fileFindings.some(f => f.severity === 'medium')) return 'medium';
    return 'low';
  };

  return (
    <div className="py-2">
      <div className="px-4 py-2 text-xs font-semibold text-text-secondary uppercase tracking-wider">
        Files Changed
      </div>
      <ul>
        {files.map(file => {
          const fileFindings = findings.filter(f => f.file === file.filename);
          const highestSev = getHighestSeverity(fileFindings);
          const isSelected = selected === file.filename;
          
          return (
            <li key={file.filename}>
              <button
                onClick={() => onSelect(file.filename)}
                className={`w-full text-left px-4 py-2 text-sm flex items-center justify-between transition-colors ${
                  isSelected ? 'bg-surface-overlay text-text-primary' : 'text-text-secondary hover:bg-surface-overlay hover:text-text-primary'
                }`}
                title={file.filename}
              >
                <span className="truncate mr-2 flex-1">
                  {file.filename.split('/').pop()}
                </span>
                {fileFindings.length > 0 && highestSev && (
                  <span className={`px-1.5 py-0.5 text-[10px] rounded border font-medium ${getSeverityColor(highestSev)}`}>
                    {fileFindings.length}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
