import type { UUID } from "./types";

export const routes = {
  health: () => `/health`,

  sites: () => `/sites`,
  site: (siteId: UUID) => `/sites/${siteId}`,

  pages: (siteId: UUID) => `/sites/${siteId}/pages`,
  page: (siteId: UUID, pageId: UUID) => `/sites/${siteId}/pages/${pageId}`,

  jobs: (siteId: UUID) => `/sites/${siteId}/analysis-jobs`,
  job: (siteId: UUID, jobId: UUID) => `/sites/${siteId}/analysis-jobs/${jobId}`,
  runJob: (siteId: UUID, jobId: UUID) => `/sites/${siteId}/analysis-jobs/${jobId}/run`,

  results: (siteId: UUID) => `/sites/${siteId}/analysis-results`,
  result: (siteId: UUID, resultId: UUID) => `/sites/${siteId}/analysis-results/${resultId}`,
  report: (siteId: UUID, resultId: UUID) => `/sites/${siteId}/analysis-results/${resultId}/report`,
  regenReport: (siteId: UUID, resultId: UUID) => `/sites/${siteId}/analysis-results/${resultId}/report/regenerate`,
};
