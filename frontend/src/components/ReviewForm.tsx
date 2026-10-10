import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { submitReview } from '../api';

export default function ReviewForm() {
  const navigate = useNavigate();
  const [owner, setOwner] = useState('');
  const [repo, setRepo] = useState('');
  const [pr, setPr] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedOwner = owner.trim();
    const normalizedRepo = repo.trim();
    const prNumber = Number(pr);
    if (!/^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/.test(normalizedOwner) || normalizedOwner.length > 39) {
      setError('Enter a valid GitHub owner name.');
      return;
    }
    if (!/^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,98}[A-Za-z0-9])?$/.test(normalizedRepo) || normalizedRepo.length > 100) {
      setError('Enter a valid GitHub repository name.');
      return;
    }
    if (!Number.isSafeInteger(prNumber) || prNumber < 1 || prNumber > 2_147_483_647) {
      setError('Enter a valid pull request number.');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const result = await submitReview(normalizedOwner, normalizedRepo, prNumber, githubToken.trim() || undefined);
      navigate(`/reviews/${result.summary.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Review could not be started. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <Link to="/" className="mb-5 inline-flex items-center gap-2 text-sm text-text-secondary hover:text-text-primary"><span aria-hidden="true">←</span> Back to reviews</Link>
      <div className="grid overflow-hidden rounded-2xl border border-border bg-surface-raised shadow-2xl shadow-black/20 md:grid-cols-[0.9fr_1.1fr]">
        <aside className="border-b border-border bg-gradient-to-br from-accent/10 via-surface-raised to-surface-raised p-7 md:border-b-0 md:border-r sm:p-9">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Pull request analysis</p>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-text-primary">Know what changed.<br />Catch what matters.</h1>
          <p className="mt-4 text-sm leading-6 text-text-secondary">Review Studio checks a pull request for security issues, bugs, and performance risks, then pins findings to the changed code.</p>
          <div className="mt-8 space-y-4">
            <Feature title="Focused findings" text="High confidence signals, grouped by file and severity." />
            <Feature title="Context in view" text="Inspect the original diff alongside each recommendation." />
            <Feature title="Private by default" text="Your GitHub token is used for this request and is not saved in review history." />
          </div>
        </aside>

        <section className="p-6 sm:p-9">
          <h2 className="text-lg font-semibold text-text-primary">Start a review</h2>
          <p className="mt-1 text-sm text-text-secondary">Enter the repository and pull request you want to analyze.</p>
          {error && <div role="alert" className="mt-5 rounded-lg border border-severity-critical/30 bg-severity-critical/10 p-3 text-sm text-severity-critical">{error}</div>}

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Owner or organization" hint="The account that owns the repo">
                <input autoComplete="off" required maxLength={39} className="input" placeholder="acme" value={owner} onChange={(event) => setOwner(event.target.value)} disabled={loading} />
              </Field>
              <Field label="Repository" hint="The repository name">
                <input autoComplete="off" required maxLength={100} className="input" placeholder="web-platform" value={repo} onChange={(event) => setRepo(event.target.value)} disabled={loading} />
              </Field>
            </div>
            <Field label="Pull request number" hint="Find this in the GitHub PR URL">
              <div className="relative"><span className="pointer-events-none absolute left-3 top-2 text-sm text-text-muted">#</span><input required type="number" min="1" step="1" className="input pl-7" placeholder="42" value={pr} onChange={(event) => setPr(event.target.value)} disabled={loading} /></div>
            </Field>
            <details className="group rounded-lg border border-border bg-surface p-4">
              <summary className="cursor-pointer list-none text-sm font-medium text-text-primary marker:hidden">Need access to a private repository?<span className="float-right text-text-muted group-open:rotate-180">⌄</span></summary>
              <p className="mt-2 text-xs leading-5 text-text-secondary">Provide a GitHub token with read access to this repository. It is sent only to this review request and is not stored.</p>
              <label htmlFor="github-token" className="sr-only">GitHub token</label>
              <input id="github-token" type="password" autoComplete="new-password" className="input mt-3" placeholder="GitHub personal access token" value={githubToken} onChange={(event) => setGithubToken(event.target.value)} disabled={loading} />
            </details>
            <button type="submit" className="btn btn-primary w-full border-accent bg-accent text-surface hover:bg-accent/90" disabled={loading}>
              {loading ? <><span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-surface/30 border-t-surface" />Reviewing pull request…</> : 'Analyze pull request'}
            </button>
            <p className="text-center text-xs text-text-muted">Large pull requests may take a few minutes to analyze.</p>
          </form>
        </section>
      </div>
    </div>
  );
}

function Field({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return <div><label className="mb-1 block text-sm font-medium text-text-primary">{label}</label>{children}<p className="mt-1 text-xs text-text-muted">{hint}</p></div>;
}

function Feature({ title, text }: { title: string; text: string }) {
  return <div className="flex gap-3"><span className="mt-0.5 grid h-6 w-6 flex-none place-items-center rounded-full border border-accent/30 bg-accent/10 text-xs text-accent">✓</span><div><p className="text-sm font-medium text-text-primary">{title}</p><p className="mt-1 text-xs leading-5 text-text-secondary">{text}</p></div></div>;
}
