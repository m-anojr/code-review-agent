import { useEffect, useState } from 'react';
import { fetchEvalReport } from '../api';
import type { EvalReport as EvalReportType } from '../types';

export default function EvalReport() {
  const [report, setReport] = useState<EvalReportType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchEvalReport()
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-text-secondary">Running evaluation suite...</div>;
  if (error) return <div className="p-8 text-severity-critical">Error: {error}</div>;
  if (!report) return null;

  return (
    <div className="p-8 max-w-5xl mx-auto w-full">
      <h2 className="text-xl font-medium text-text-primary mb-6">Evaluation Report</h2>

      <div className="grid grid-cols-4 gap-4 mb-8">
        <div className="border border-border bg-surface-raised p-4 rounded-md">
          <div className="text-sm text-text-secondary mb-1">Total Fixtures</div>
          <div className="text-2xl font-mono text-text-primary">{report.total_fixtures}</div>
        </div>
        <div className="border border-border bg-surface-raised p-4 rounded-md">
          <div className="text-sm text-text-secondary mb-1">Precision</div>
          <div className="text-2xl font-mono text-text-primary">{report.precision.toFixed(3)}</div>
        </div>
        <div className="border border-border bg-surface-raised p-4 rounded-md">
          <div className="text-sm text-text-secondary mb-1">Recall</div>
          <div className="text-2xl font-mono text-text-primary">{report.recall.toFixed(3)}</div>
        </div>
        <div className="border border-border bg-surface-raised p-4 rounded-md">
          <div className="text-sm text-text-secondary mb-1">F1 Score</div>
          <div className="text-2xl font-mono text-text-primary">{report.f1.toFixed(3)}</div>
        </div>
      </div>

      <div className="border border-border rounded-md overflow-hidden bg-surface-raised">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-text-secondary bg-surface uppercase border-b border-border">
            <tr>
              <th className="px-6 py-3 font-medium">Fixture</th>
              <th className="px-6 py-3 font-medium text-right">True Positives</th>
              <th className="px-6 py-3 font-medium text-right">False Positives</th>
              <th className="px-6 py-3 font-medium text-right">False Negatives</th>
            </tr>
          </thead>
          <tbody>
            {report.details.map((d) => (
              <tr key={d.fixture} className="border-b border-border last:border-0 hover:bg-surface-overlay">
                <td className="px-6 py-4 font-mono text-text-primary">{d.fixture}</td>
                <td className="px-6 py-4 text-right">
                  <span className={d.true_positives > 0 ? 'text-accent' : 'text-text-muted'}>{d.true_positives}</span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={d.false_positives > 0 ? 'text-severity-high' : 'text-text-muted'}>{d.false_positives}</span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={d.false_negatives > 0 ? 'text-severity-critical' : 'text-text-muted'}>{d.false_negatives}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
