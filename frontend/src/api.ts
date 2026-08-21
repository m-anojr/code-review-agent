import type { ReviewDetail, ReviewSummary, EvalReport, HealthStatus } from './types';

const API_BASE = '/api';

export async function fetchReviews(): Promise<ReviewSummary[]> {
  const res = await fetch(`${API_BASE}/reviews`);
  if (!res.ok) throw new Error('Failed to fetch reviews');
  return res.json();
}

export async function fetchReview(id: string): Promise<ReviewDetail> {
  const res = await fetch(`${API_BASE}/reviews/${id}`);
  if (!res.ok) throw new Error('Failed to fetch review');
  return res.json();
}

export async function submitReview(owner: string, repo: string, pr_number: number, github_token?: string): Promise<ReviewDetail> {
  const res = await fetch(`${API_BASE}/reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ owner, repo, pr_number, github_token }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || 'Failed to submit review');
  }
  return res.json();
}

export async function fetchEvalReport(): Promise<EvalReport> {
  const res = await fetch(`${API_BASE}/eval`);
  if (!res.ok) throw new Error('Failed to fetch eval report');
  return res.json();
}

export async function fetchHealth(): Promise<HealthStatus> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to fetch health status');
  return res.json();
}
