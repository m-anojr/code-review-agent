export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type Category = 'bug' | 'security' | 'style' | 'performance';

export interface Finding {
  file: string;
  line_start: number;
  line_end: number;
  severity: Severity;
  category: Category;
  explanation: string;
  suggested_fix: string;
  source: string;
}

export interface Hunk {
  old_start: number;
  old_count: number;
  new_start: number;
  new_count: number;
  lines: string[];
  header: string;
}

export interface FileDiff {
  filename: string;
  old_filename: string | null;
  hunks: Hunk[];
  is_new: boolean;
  is_deleted: boolean;
  raw_header: string;
}

export interface ReviewSummary {
  id: string;
  owner: string;
  repo: string;
  pr_number: number;
  pr_title: string;
  created_at: string;
  critical: number;
  high: number;
  medium: number;
  low: number;
  files_analyzed: number;
}

export interface ReviewDetail {
  summary: ReviewSummary;
  findings: Finding[];
  file_diffs: FileDiff[];
}

export interface EvalFixtureResult {
  fixture: string;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  precision: number;
  recall: number;
}

export interface EvalReport {
  precision: number;
  recall: number;
  f1: number;
  total_fixtures: number;
  details: EvalFixtureResult[];
}
