import { apiFetch } from "./client";
import { routes } from "./routes";
import type {
  Site,
  Page,
  UUID,
  DeviceType,
  AnalysisJob,
  AnalysisJobTarget,
  AnalysisResultListItem,
  AnalysisResult,
  Report,
  PageType,
} from "./types";

// Sites
export async function listSites(): Promise<{ items: Site[] }> {
  return apiFetch(routes.sites());
}

export async function createSite(input: { name: string }): Promise<Site> {
  return apiFetch(routes.sites(), { method: "POST", body: input });
}

export async function getSite(siteId: UUID): Promise<Site> {
  return apiFetch(routes.site(siteId));
}

export async function deleteSite(siteId: UUID): Promise<void> {
  return apiFetch(routes.site(siteId), { method: "DELETE" });
}

// Pages
export async function listPages(siteId: UUID): Promise<{ items: Page[] }> {
  return apiFetch(routes.pages(siteId));
}

export async function createPage(
  siteId: UUID,
  input: { url: string; page_type: PageType; label?: string }
): Promise<Page> {
  return apiFetch(routes.pages(siteId), { method: "POST", body: input });
}

export async function updatePage(
  siteId: UUID,
  pageId: UUID,
  input: Partial<{ label: string; page_type: PageType }>
): Promise<Page> {
  return apiFetch(routes.page(siteId, pageId), { method: "PATCH", body: input });
}

export async function deletePage(
  siteId: UUID,
  pageId: UUID
): Promise<{ deleted: boolean }> {
  return apiFetch(routes.page(siteId, pageId), { method: "DELETE" });
}

// Jobs
export async function createAnalysisJob(
  siteId: UUID,
  input: {
    device: DeviceType;
    locale: string;
    target_country: string;
    enable_pagespeed: boolean;
    enable_gsc: boolean;
    enable_ai_report: boolean;
    gsc_property?: string;
    brand_terms?: string[];
    targets: AnalysisJobTarget[];
  }
): Promise<{ job_id: UUID; status: string; created_at: string }> {
  return apiFetch(routes.jobs(siteId), { method: "POST", body: input });
}

export async function listJobs(siteId: UUID): Promise<{ items: AnalysisJob[] }> {
  return apiFetch(routes.jobs(siteId));
}

export async function getJob(siteId: UUID, jobId: UUID): Promise<AnalysisJob> {
  return apiFetch(routes.job(siteId, jobId));
}

export async function runJob(
  siteId: UUID,
  jobId: UUID
): Promise<{ ok: boolean }> {
  return apiFetch(routes.runJob(siteId, jobId), { method: "POST" });
}

// Results
export async function listResults(
  siteId: UUID,
  limit = 20
): Promise<{ items: AnalysisResultListItem[] }> {
  return apiFetch(`${routes.results(siteId)}?limit=${limit}`);
}

export async function getResult(
  siteId: UUID,
  resultId: UUID
): Promise<AnalysisResult> {
  return apiFetch(routes.result(siteId, resultId));
}

export async function getReport(siteId: UUID, resultId: UUID): Promise<Report> {
  return apiFetch(routes.report(siteId, resultId));
}

export async function regenerateReport(
  siteId: UUID,
  resultId: UUID,
  input?: { report_style?: "consultant" | "concise" | "technical" }
): Promise<{ ok: boolean; report_id: UUID }> {
  return apiFetch(routes.regenReport(siteId, resultId), {
    method: "POST",
    body: input || {},
  });
}
