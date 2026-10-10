import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchReviews } from '../api';
import type { ReviewSummary, Severity } from '../types';

const severities: Severity[] = ['critical', 'high', 'medium', 'low'];
const metricTone: Record<string, string> = {
  neutral: 'text-text-primary',
  critical: 'text-severity-critical',
  high: 'text-severity-high',
  medium: 'text-severity-medium',
  low: 'text-severity-low',
};
const badgeTone: Record<Severity, string> = {
  critical: 'bg-severity-critical/10 text-severity-critical',
  high: 'bg-severity-high/10 text-severity-high',
  medium: 'bg-severity-medium/10 text-severity-medium',
  low: 'bg-severity-low/10 text-severity-low',
};

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown date';
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

export default function ReviewList() {
  const [reviews, setReviews] = useState<ReviewSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState<Severity | 'all'>('all');

  const loadReviews = useCallback(async (quiet = false) => {
    if (quiet) setRefreshing(true);
    else setLoading(true);
    setError('');
    try {
      setReviews(await fetchReviews());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load reviews.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { void loadReviews(); }, [loadReviews]);

  const totals = useMemo(() => reviews.reduce((sum, review) => {
    sum.critical += review.critical;
    sum.high += review.high;
    sum.medium += review.medium;
    sum.low += review.low;
    return sum;
  }, { critical: 0, high: 0, medium: 0, low: 0 }), [reviews]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return reviews.filter((review) => {
      const matchesText = !needle || `${review.owner}/${review.repo} ${review.pr_title} #${review.pr_number}`.toLowerCase().includes(needle);
      const matchesSeverity = severity === 'all' || review[severity] > 0;
      return matchesText && matchesSeverity;
    });
  }, [reviews, query, severity]);

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-accent">Code quality workspace</p>
          <h1 className="text-3xl font-semibold tracking-tight text-text-primary">Review dashboard</h1>
          <p className="mt-2 text-sm text-text-secondary">Track pull request reviews and surface the issues that need attention.</p>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" onClick={() => void loadReviews(true)} disabled={loading || refreshing} className="btn border-border bg-surface-raised text-text-secondary hover:text-text-primary">
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
          <Link to="/reviews/new" className="btn btn-primary">New review <span aria-hidden="true" className="ml-2">＋</span></Link>
        </div>
      </div>

      <div className="mb-8 grid grid-cols-2 gap-3 lg:grid-cols-5">
        <Metric label="Reviews" value={reviews.length} tone="neutral" />
        <Metric label="Critical" value={totals.critical} tone="critical" />
        <Metric label="High" value={totals.high} tone="high" />
        <Metric label="Medium" value={totals.medium} tone="medium" />
        <Metric label="Low" value={totals.low} tone="low" />
      </div>

      <section className="overflow-hidden rounded-xl border border-border bg-surface-raised shadow-xl shadow-black/10">
        <div className="flex flex-col gap-3 border-b border-border p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="font-semibold text-text-primary">Recent reviews</h2>
            <p className="mt-1 text-xs text-text-secondary">{loading ? 'Loading review history…' : `${filtered.length} of ${reviews.length} reviews`}</p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <label className="sr-only" htmlFor="review-search">Search reviews</label>
            <input id="review-search" className="input w-full sm:w-64" placeholder="Search repo or PR…" value={query} onChange={(event) => setQuery(event.target.value)} />
            <label className="sr-only" htmlFor="severity-filter">Filter by severity</label>
            <select id="severity-filter" className="input sm:w-40" value={severity} onChange={(event) => setSeverity(event.target.value as Severity | 'all')}>
              <option value="all">All findings</option>
              {severities.map((item) => <option key={item} value={item}>{item[0].toUpperCase() + item.slice(1)} issues</option>)}
            </select>
          </div>
        </div>

        {error ? (
          <div role="alert" className="m-5 rounded-lg border border-severity-critical/30 bg-severity-critical/10 p-4">
            <p className="text-sm font-medium text-severity-critical">Review history is unavailable</p>
            <p className="mt-1 text-sm text-text-secondary">{error}</p>
            <button type="button" className="mt-3 text-sm font-medium text-accent hover:underline" onClick={() => void loadReviews()}>Try again</button>
          </div>
        ) : loading ? (
          <div className="space-y-3 p-5" aria-label="Loading reviews"><div className="h-12 animate-pulse rounded bg-surface-overlay" /><div className="h-12 animate-pulse rounded bg-surface-overlay" /><div className="h-12 animate-pulse rounded bg-surface-overlay" /></div>
        ) : filtered.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-xl border border-border bg-surface text-xl text-accent">⌕</div>
            <h3 className="font-medium text-text-primary">{reviews.length === 0 ? 'Your review history starts here' : 'No reviews match those filters'}</h3>
            <p className="mx-auto mt-2 max-w-md text-sm text-text-secondary">{reviews.length === 0 ? 'Analyze a GitHub pull request to get a focused summary of security, correctness, and quality findings.' : 'Try a different search, or clear the severity filter.'}</p>
            {reviews.length === 0 && <Link to="/reviews/new" className="btn btn-primary mt-5">Analyze your first PR</Link>}
            {reviews.length > 0 && <button type="button" className="mt-4 text-sm text-accent hover:underline" onClick={() => { setQuery(''); setSeverity('all'); }}>Clear filters</button>}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-surface text-xs uppercase tracking-wide text-text-secondary">
                <tr><th className="px-5 py-3 font-medium">Pull request</th><th className="px-5 py-3 font-medium">Reviewed</th><th className="px-5 py-3 font-medium">Files</th>{severities.map((item) => <th key={item} className="px-3 py-3 text-right font-medium">{item}</th>)}<th className="px-5 py-3" /></tr>
              </thead>
              <tbody>
                {filtered.map((review) => <ReviewRow key={review.id} review={review} />)}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone: string }) {
  return <div className="rounded-xl border border-border bg-surface-raised p-4"><p className="text-xs font-medium text-text-secondary">{label}</p><p className={`mt-2 text-2xl font-semibold tabular-nums ${metricTone[tone]}`}>{value.toLocaleString()}</p></div>;
}

function ReviewRow({ review }: { review: ReviewSummary }) {
  const total = review.critical + review.high + review.medium + review.low;
  return (
    <tr className="border-t border-border transition-colors hover:bg-surface-overlay/60">
      <td className="px-5 py-4"><Link to={`/reviews/${review.id}`} className="font-medium text-text-primary hover:text-accent">{review.owner}/{review.repo}</Link><p className="mt-1 max-w-md truncate text-xs text-text-secondary">{review.pr_title || 'Pull request'} <span className="text-text-muted">· #{review.pr_number}</span></p></td>
      <td className="whitespace-nowrap px-5 py-4 text-xs text-text-secondary">{formatDate(review.created_at)}</td>
      <td className="px-5 py-4 tabular-nums text-text-secondary">{review.files_analyzed}</td>
      {severities.map((item) => <td key={item} className="px-3 py-4 text-right"><span className={`inline-flex min-w-7 justify-center rounded-md px-2 py-1 text-xs font-semibold tabular-nums ${review[item] ? badgeTone[item] : 'text-text-muted'}`}>{review[item]}</span></td>)}
      <td className="px-5 py-4 text-right"><Link aria-label={`Open ${review.owner}/${review.repo} pull request ${review.pr_number}`} to={`/reviews/${review.id}`} className="text-text-muted hover:text-accent">→</Link><span className="sr-only">{total} total findings</span></td>
    </tr>
  );
}
