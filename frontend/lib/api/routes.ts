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
  todoDetail: (siteId: UUID, resultId: UUID, todoId: string) =>
    `/sites/${siteId}/analysis-results/${resultId}/todos/${todoId}`,

  // Progress tracking (Appendix AC)
  progress: (siteId: UUID) => `/sites/${siteId}/progress`,
  progressHistory: (siteId: UUID) => `/sites/${siteId}/progress/history`,
  progressSnapshot: (siteId: UUID) => `/sites/${siteId}/progress/snapshot`,
  progressBaseline: (siteId: UUID) => `/sites/${siteId}/progress/baseline`,

  // Time series (Appendix AD, AE, AF)
  serpTimeseries: (siteId: UUID) => `/sites/${siteId}/serp-timeseries`,
  crawlErrorsTimeseries: (siteId: UUID) => `/sites/${siteId}/crawl-errors-timeseries`,
  backlinksTimeseries: (siteId: UUID) => `/sites/${siteId}/backlinks-timeseries`,

  // Trend data for charts (Appendix AG)
  serpTrend: (siteId: UUID) => `/sites/${siteId}/timeseries/serp`,
  crawlErrorTrend: (siteId: UUID) => `/sites/${siteId}/timeseries/crawl-errors`,
  backlinkTrend: (siteId: UUID) => `/sites/${siteId}/timeseries/backlinks`,

  // Improvement story (Appendix AI)
  story: (siteId: UUID) => `/sites/${siteId}/story`,
};
