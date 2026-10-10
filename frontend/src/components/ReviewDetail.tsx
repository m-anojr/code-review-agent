import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchReview } from '../api';
import type { ReviewDetail as ReviewDetailType } from '../types';
import FileTree from './FileTree';
import DiffView from './DiffView';

const severityText: Record<'critical' | 'high' | 'medium' | 'low', string> = {
  critical: 'text-severity-critical',
  high: 'text-severity-high',
  medium: 'text-severity-medium',
  low: 'text-severity-low',
};

export default function ReviewDetail() {
  const { id } = useParams<{ id: string }>();
  const [review, setReview] = useState<ReviewDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetchReview(id)
      .then((data) => {
        setReview(data);
        if (data.file_diffs.length > 0) {
          setSelectedFile(data.file_diffs[0].filename);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-8 text-text-secondary">Loading review...</div>;
  if (error) return <div className="mx-auto max-w-xl p-8"><div role="alert" className="rounded-xl border border-severity-critical/30 bg-severity-critical/10 p-5"><h1 className="font-medium text-severity-critical">Review could not be loaded</h1><p className="mt-2 text-sm text-text-secondary">{error}</p><Link to="/" className="mt-4 inline-block text-sm text-accent hover:underline">Back to review history</Link></div></div>;
  if (!review) return null;

  const currentDiff = review.file_diffs.find((f) => f.filename === selectedFile);
  const currentFindings = review.findings.filter((f) => f.file === selectedFile);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-none border-b border-border bg-surface px-4 py-4 sm:px-6">
        <Link to="/" className="mb-3 inline-flex items-center gap-2 text-xs text-text-secondary hover:text-text-primary"><span aria-hidden="true">←</span> All reviews</Link>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-lg font-semibold text-text-primary">{review.summary.owner}/{review.summary.repo}</h1>
              <a href={`https://github.com/${encodeURIComponent(review.summary.owner)}/${encodeURIComponent(review.summary.repo)}/pull/${review.summary.pr_number}`} target="_blank" rel="noopener noreferrer" className="rounded-md border border-border bg-surface-raised px-2 py-1 text-xs text-text-secondary hover:text-accent">PR #{review.summary.pr_number} ↗</a>
            </div>
            <p className="mt-1 max-w-3xl text-sm text-text-secondary">{review.summary.pr_title || 'Pull request review'}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-md border border-border bg-surface-raised px-2.5 py-1.5 text-text-secondary">{review.summary.files_analyzed} files analyzed</span>
            <span className="rounded-md border border-border bg-surface-raised px-2.5 py-1.5 text-text-secondary">{review.findings.length} findings</span>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {(['critical', 'high', 'medium', 'low'] as const).map((level) => <span key={level} className={review.summary[level] > 0 ? `font-medium ${severityText[level]}` : 'text-text-muted'}>{review.summary[level]} {level}</span>)}
        </div>
      </div>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <div className="w-56 flex-none overflow-y-auto border-r border-border bg-surface-raised sm:w-64">
          <FileTree 
            files={review.file_diffs} 
            findings={review.findings}
            selected={selectedFile}
            onSelect={setSelectedFile}
          />
        </div>
        <div className="min-w-0 flex-1 overflow-y-auto bg-surface p-4 sm:p-6">
          {currentDiff ? (
            <>
              {currentFindings.length === 0 && <div className="mb-4 rounded-lg border border-border bg-surface-raised px-4 py-3 text-sm text-text-secondary">No findings in this file. The diff is available below for context.</div>}
              <DiffView diff={currentDiff} findings={currentFindings} />
            </>
          ) : review.file_diffs.length === 0 ? (
            <div className="mx-auto mt-10 max-w-md rounded-xl border border-border bg-surface-raised p-6 text-center"><h2 className="font-medium text-text-primary">No text diffs available</h2><p className="mt-2 text-sm text-text-secondary">This pull request may contain only binary files or files GitHub could not render as text.</p></div>
          ) : (
            <div className="mt-10 text-center text-sm text-text-secondary">Select a file to view its diff</div>
          )}
        </div>
      </div>
    </div>
  );
}
