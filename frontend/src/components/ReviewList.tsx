import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchReviews } from '../api';
import type { ReviewSummary } from '../types';

export default function ReviewList() {
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReviews()
      .then(setReviews)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="p-8 text-text-secondary">Loading...</div>;
  }

  if (reviews.length === 0) {
    return (
      <div className="p-8 flex flex-col items-center justify-center text-center max-w-md mx-auto h-full">
        <h2 className="text-lg font-medium text-text-primary mb-2">No reviews yet</h2>
        <p className="text-sm text-text-secondary mb-6">
          Submit your first pull request for analysis to see findings here.
        </p>
        <Link to="/reviews/new" className="btn btn-primary">
          Analyze PR
        </Link>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto w-full">
      <div className="border border-border rounded-md overflow-hidden bg-surface-raised">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-text-secondary bg-surface uppercase border-b border-border">
            <tr>
              <th className="px-6 py-3 font-medium">Repository</th>
              <th className="px-6 py-3 font-medium">PR</th>
              <th className="px-6 py-3 font-medium">Date</th>
              <th className="px-6 py-3 font-medium text-right">Critical</th>
              <th className="px-6 py-3 font-medium text-right">High</th>
              <th className="px-6 py-3 font-medium text-right">Medium</th>
              <th className="px-6 py-3 font-medium text-right">Low</th>
            </tr>
          </thead>
          <tbody>
            {reviews.map((r) => (
              <tr key={r.id} className="border-b border-border last:border-0 hover:bg-surface-overlay transition-colors">
                <td className="px-6 py-4">
                  <Link to={`/reviews/${r.id}`} className="text-text-primary hover:text-accent font-medium">
                    {r.owner}/{r.repo}
                  </Link>
                </td>
                <td className="px-6 py-4 text-text-secondary">
                  <a
                    href={`https://github.com/${r.owner}/${r.repo}/pull/${r.pr_number}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-text-primary hover:underline"
                  >
                    #{r.pr_number}
                  </a>
                </td>
                <td className="px-6 py-4 text-text-secondary">
                  {new Date(r.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${r.critical > 0 ? 'bg-severity-critical/20 text-severity-critical' : 'text-text-muted'}`}>
                    {r.critical}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${r.high > 0 ? 'bg-severity-high/20 text-severity-high' : 'text-text-muted'}`}>
                    {r.high}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${r.medium > 0 ? 'bg-severity-medium/20 text-severity-medium' : 'text-text-muted'}`}>
                    {r.medium}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${r.low > 0 ? 'bg-severity-low/20 text-severity-low' : 'text-text-muted'}`}>
                    {r.low}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
