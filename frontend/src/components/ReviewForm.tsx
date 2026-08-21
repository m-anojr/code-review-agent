import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { submitReview } from '../api';

export default function ReviewForm() {
  const navigate = useNavigate();
  const [owner, setOwner] = useState('');
  const [repo, setRepo] = useState('');
  const [pr, setPr] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!owner || !repo || !pr) return;

    setLoading(true);
    setError('');

    try {
      const res = await submitReview(owner, repo, parseInt(pr, 10), githubToken || undefined);
      navigate(`/reviews/${res.summary.id}`);
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-md mx-auto w-full">
      <div className="border border-border rounded-md bg-surface-raised p-6">
        <h2 className="text-lg font-medium text-text-primary mb-1">New Review</h2>
        <p className="text-sm text-text-secondary mb-6">
          Submit a GitHub pull request for analysis.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-severity-critical/10 border border-severity-critical/20 rounded text-sm text-severity-critical">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Owner / Organization
            </label>
            <input
              type="text"
              required
              className="input"
              placeholder="e.g. facebook"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              Repository
            </label>
            <input
              type="text"
              required
              className="input"
              placeholder="e.g. react"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              PR Number
            </label>
            <input
              type="number"
              required
              min="1"
              className="input"
              placeholder="e.g. 12345"
              value={pr}
              onChange={(e) => setPr(e.target.value)}
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-1">
              GitHub Token (Optional, for private repos)
            </label>
            <input
              type="password"
              className="input"
              placeholder="ghp_..."
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              disabled={loading}
            />
          </div>
          
          <button
            type="submit"
            className="btn btn-primary w-full mt-2 bg-accent text-[#000] border-accent hover:bg-accent/90"
            disabled={loading}
          >
            {loading ? 'Analyzing...' : 'Start Review'}
          </button>
        </form>
      </div>
    </div>
  );
}
