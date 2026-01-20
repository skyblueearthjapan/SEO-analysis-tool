export type UUID = string;

export type PageType = "official_homepage" | "competitor_page" | "third_party_profile_page";
export type DeviceType = "mobile" | "desktop";

export type JobStatus = "queued" | "running" | "done" | "failed";

export type MainCause = "content_quality" | "ctr" | "technical" | "mixed" | "unknown";
export type ScoreGrade = "A" | "B" | "C" | "D";

export type TodoPriority = "P0" | "P1" | "P2";
export type TodoCategory = "content" | "technical" | "ctr" | "outreach" | "internal_linking";

export interface Site {
  site_id: UUID;
  name: string;
  created_at: string;
}

export interface Page {
  page_id: UUID;
  site_id: UUID;
  url: string;
  page_type: PageType;
  label?: string | null;
  created_at: string;
}

export interface AnalysisJobTarget {
  page_id: UUID;
  role: "official" | "competitor" | "third_party";
  sort_order: number;
}

export interface AnalysisJob {
  job_id: UUID;
  site_id: UUID;
  status: JobStatus;
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  targets?: AnalysisJobTarget[];
}

export interface Diagnosis {
  main_cause: MainCause;
  cause_breakdown: { content_quality: number; ctr: number; technical: number };
  scores: { content: ScoreGrade; technical: ScoreGrade; ctr: ScoreGrade };
  evidence: { claim: string; support: string[] }[];
}

export type Likelihood = "high" | "medium" | "low";
export type Severity = "critical" | "warning" | "info";
export type TemplateType = "text" | "code" | "bullets";

export interface RootCause {
  label: string;
  likelihood: Likelihood;
  notes?: string;
}

export interface EvidenceItem {
  id: string;
  title: string;
  kind: string;
  severity: Severity;
  data: Record<string, any>;
}

export interface Step {
  text: string;
  done: boolean;
}

export interface Template {
  title: string;
  type: TemplateType;
  language?: string;
  content: string;
}

export interface Verification {
  metric: string;
  target: string;
  how_to_check: string;
}

export interface TodoDetail {
  why: string;
  root_causes: RootCause[];
  evidence: EvidenceItem[];
  steps: Step[];
  templates: Template[];
  verification: Verification[];
  related_todo_ids: string[];
}

export interface Todo {
  todo_id: UUID;
  priority: TodoPriority;
  category: TodoCategory;
  title: string;
  details: string;
  evidence: string[];
  impact: "high" | "medium" | "low";
  effort: "small" | "medium" | "large";
  examples?: {
    title_variants?: string[];
    meta_description_variants?: string[];
    h2_outline?: string[];
    faq_questions?: string[];
    outreach_message_draft_jp?: string;
  };
  detail?: TodoDetail;
}

export interface AnalysisResultListItem {
  result_id: UUID;
  job_id: UUID;
  generated_at: string;
  diagnosis_main_cause?: MainCause | null;
}

export interface AnalysisResult {
  result_id: UUID;
  job_id: UUID;
  generated_at: string;
  analysis_json: any;
}

export interface Report {
  result_id: UUID;
  report_markdown: string;
}
