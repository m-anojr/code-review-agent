import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchReview } from '../api';
import type { ReviewDetail as ReviewDetailType } from '../types';
import FileTree from './FileTree';
import DiffView from './DiffView';

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
  if (error) return <div className="p-8 text-severity-critical">Error: {error}</div>;
  if (!review) return null;

  const currentDiff = review.file_diffs.find((f) => f.filename === selectedFile);
  const currentFindings = review.findings.filter((f) => f.file === selectedFile);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="flex-none border-b border-border bg-surface px-6 py-4">
        <h1 className="text-xl font-semibold text-text-primary mb-1">
          {review.summary.owner}/{review.summary.repo} <span className="text-text-secondary font-normal">#{review.summary.pr_number}</span>
        </h1>
        <div className="flex gap-4 text-sm text-text-secondary">
          <span>{review.summary.files_analyzed} files analyzed</span>
          <span className="text-border">|</span>
          <span className="flex gap-2">
            Findings:
            <span className={review.summary.critical > 0 ? 'text-severity-critical font-medium' : ''}>{review.summary.critical} critical</span>,
            <span className={review.summary.high > 0 ? 'text-severity-high font-medium' : ''}>{review.summary.high} high</span>,
            <span className={review.summary.medium > 0 ? 'text-severity-medium font-medium' : ''}>{review.summary.medium} medium</span>,
            <span className={review.summary.low > 0 ? 'text-severity-low font-medium' : ''}>{review.summary.low} low</span>
          </span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-64 flex-none border-r border-border bg-surface-raised overflow-y-auto">
          <FileTree 
            files={review.file_diffs} 
            findings={review.findings}
            selected={selectedFile}
            onSelect={setSelectedFile}
          />
        </div>
        <div className="flex-1 overflow-y-auto bg-surface p-6">
          {currentDiff ? (
            <DiffView diff={currentDiff} findings={currentFindings} />
          ) : (
            <div className="text-text-secondary text-center mt-10">Select a file to view its diff</div>
          )}
        </div>
      </div>
    </div>
  );
}
