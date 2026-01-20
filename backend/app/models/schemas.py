"""
Pydantic models for SEO Analysis API
Based on spec.md JSON Schema definitions
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


# ============================================================
# Enums
# ============================================================

class PageType(str, Enum):
    OFFICIAL = "official_homepage"
    COMPETITOR = "competitor_page"
    THIRD_PARTY = "third_party_profile_page"


class DeviceType(str, Enum):
    MOBILE = "mobile"
    DESKTOP = "desktop"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class MainCause(str, Enum):
    CONTENT_QUALITY = "content_quality"
    CTR = "ctr"
    TECHNICAL = "technical"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class ScoreGrade(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class TodoPriority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"


class TodoCategory(str, Enum):
    CONTENT = "content"
    TECHNICAL = "technical"
    CTR = "ctr"
    OUTREACH = "outreach"
    INTERNAL_LINKING = "internal_linking"


class TodoImpact(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TodoEffort(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class QueryIntent(str, Enum):
    BRAND = "brand"
    INFO = "info"
    COMPARE = "compare"
    PRICE = "price"
    VISIT = "visit"
    UNKNOWN = "unknown"


class MobileFriendlyHint(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    NOT_AVAILABLE = "not_available"


class TargetRole(str, Enum):
    OFFICIAL = "official"
    COMPETITOR = "competitor"
    THIRD_PARTY = "third_party"


class AnalysisCheckStatus(str, Enum):
    """Analysis check execution status (Appendix V)"""
    DONE = "done"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    NOT_SUPPORTED = "not_supported"


class AnalysisCheckCode(str, Enum):
    """Analysis check codes (Appendix V)"""
    FETCH = "fetch"
    HTML_BASIC = "html_basic"
    HEADINGS = "headings"
    TEXT_STATS = "text_stats"
    LINKS = "links"
    IMAGES_ALT = "images_alt"
    STRUCTURED_DATA = "structured_data"
    PAGESPEED = "pagespeed"
    SEARCH_CONSOLE = "search_console"
    INTENT_COVERAGE = "intent_coverage"
    COMPETITOR_DIFF = "competitor_diff"
    BACKLINKS = "backlinks"
    SERP_RANK = "serp_rank"
    KEYWORD_RESEARCH = "keyword_research"
    SITE_CRAWL = "site_crawl"
    LOG_ANALYSIS = "log_analysis"
    DUPLICATE_CANNIBALIZATION = "duplicate_cannibalization"


class SnapshotType(str, Enum):
    """Progress snapshot type (Appendix AC)"""
    BEFORE = "before"
    AFTER = "after"
    PERIODIC = "periodic"


class DraftStatus(str, Enum):
    """Content draft status (Appendix AO)"""
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"


class TodoStatus(str, Enum):
    """Todo item completion status (Appendix T)"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    WONT_FIX = "wont_fix"


# ============================================================
# Site Models
# ============================================================

class SiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class SiteResponse(BaseModel):
    site_id: UUID
    name: str
    created_at: datetime


class SiteListResponse(BaseModel):
    items: List[SiteResponse]


# ============================================================
# Page Models
# ============================================================

class PageCreate(BaseModel):
    url: str = Field(..., min_length=1)
    page_type: PageType
    label: Optional[str] = None


class PageUpdate(BaseModel):
    label: Optional[str] = None
    page_type: Optional[PageType] = None


class PageResponse(BaseModel):
    page_id: UUID
    site_id: UUID
    url: str
    page_type: PageType
    label: Optional[str]
    created_at: datetime


class PageListResponse(BaseModel):
    items: List[PageResponse]


class PageDeleteResponse(BaseModel):
    deleted: bool


# ============================================================
# Analysis Job Models
# ============================================================

class AnalysisJobTarget(BaseModel):
    page_id: UUID
    role: TargetRole
    sort_order: int = 0


class AnalysisJobCreate(BaseModel):
    device: DeviceType = DeviceType.MOBILE
    locale: str = "ja-JP"
    target_country: str = "JP"
    enable_pagespeed: bool = True
    enable_gsc: bool = False
    enable_ai_report: bool = True
    gsc_property: Optional[str] = None
    brand_terms: Optional[List[str]] = None
    targets: List[AnalysisJobTarget]


class AnalysisJobResponse(BaseModel):
    job_id: UUID
    site_id: UUID
    status: JobStatus
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    targets: Optional[List[AnalysisJobTarget]] = None


class AnalysisJobListResponse(BaseModel):
    items: List[AnalysisJobResponse]


class AnalysisJobRunResponse(BaseModel):
    ok: bool


# ============================================================
# Analysis Result Sub-Models
# ============================================================

class FetchResult(BaseModel):
    status_code: int
    final_url: str
    redirect_chain: List[str] = []


class Headings(BaseModel):
    h1: List[str] = []
    h2: List[str] = []
    h3: List[str] = []


class TextStats(BaseModel):
    text_length_chars: int = 0
    text_length_words_est: int = 0


class LinksInfo(BaseModel):
    internal_count: int = 0
    external_count: int = 0
    external_domains: List[str] = []


class ImagesInfo(BaseModel):
    count: int = 0
    with_alt: int = 0
    alt_ratio: float = 0.0


class StructuredData(BaseModel):
    types: List[str] = []
    has_faq_schema: bool = False
    has_organization_schema: bool = False
    has_article_schema: bool = False


class HtmlAnalysis(BaseModel):
    title: str = ""
    meta_description: str = ""
    canonical: str = ""
    robots_meta: str = ""
    headings: Headings = Field(default_factory=Headings)
    text_stats: TextStats = Field(default_factory=TextStats)
    links: LinksInfo = Field(default_factory=LinksInfo)
    images: ImagesInfo = Field(default_factory=ImagesInfo)
    structured_data: StructuredData = Field(default_factory=StructuredData)


class PageSpeedResult(BaseModel):
    available: bool = False
    performance_score: Optional[int] = None
    lcp_ms: Optional[int] = None
    inp_ms: Optional[int] = None
    cls: Optional[float] = None


class TechAnalysis(BaseModel):
    mobile_friendly_hint: MobileFriendlyHint = MobileFriendlyHint.NOT_AVAILABLE
    pagespeed: PageSpeedResult = Field(default_factory=PageSpeedResult)


class ContentAnalysis(BaseModel):
    intent_coverage: Dict[str, float] = {}
    missing_sections: List[str] = []
    notes: List[str] = []


class SerpTopResult(BaseModel):
    rank: int
    url: str
    title: str
    snippet: str = ""


class SerpSnapshot(BaseModel):
    available: bool = False
    queries_tested: List[str] = []
    serp_features: List[str] = []
    top_results: List[SerpTopResult] = []


class TopQuery(BaseModel):
    query: str
    impressions: int
    clicks: int
    ctr: float
    position: float
    query_intent: QueryIntent = QueryIntent.UNKNOWN


class BrandQuerySummary(BaseModel):
    brand_queries_present: bool = False
    brand_impressions: int = 0
    brand_ctr: float = 0.0


class SearchConsoleData(BaseModel):
    available: bool = False
    time_window_days: Optional[int] = None
    top_queries: List[TopQuery] = []
    brand_query_summary: BrandQuerySummary = Field(default_factory=BrandQuerySummary)


class PageAnalysis(BaseModel):
    page_id: str
    url: str
    page_type: PageType
    fetch: FetchResult
    html: HtmlAnalysis
    tech: TechAnalysis
    content: ContentAnalysis
    serp: SerpSnapshot
    search_console: SearchConsoleData


# ============================================================
# Comparison Models
# ============================================================

class StructureDiff(BaseModel):
    h2_count_delta: int = 0
    missing_intent_items: List[str] = []
    faq_schema_delta: int = 0


class TechDiff(BaseModel):
    performance_score_delta: Optional[int] = None
    mobile_hint_delta: str = ""


class SerpDiff(BaseModel):
    title_pattern_notes: List[str] = []
    snippet_pattern_notes: List[str] = []


class ComparisonDiff(BaseModel):
    structure: StructureDiff = Field(default_factory=StructureDiff)
    tech: TechDiff = Field(default_factory=TechDiff)
    serp: SerpDiff = Field(default_factory=SerpDiff)


class Comparison(BaseModel):
    comparison_id: str
    kind: str  # "official_vs_competitor" | "official_vs_third_party"
    source_page_id: str
    target_page_id: str
    diff: ComparisonDiff


# ============================================================
# Diagnosis Models
# ============================================================

class CauseBreakdown(BaseModel):
    content_quality: int = 0
    ctr: int = 0
    technical: int = 0


class Scores(BaseModel):
    content: ScoreGrade = ScoreGrade.D
    technical: ScoreGrade = ScoreGrade.D
    ctr: ScoreGrade = ScoreGrade.D


class Evidence(BaseModel):
    claim: str
    support: List[str]


class Diagnosis(BaseModel):
    main_cause: MainCause
    cause_breakdown: CauseBreakdown
    scores: Scores
    evidence: List[Evidence] = []


# ============================================================
# Todo Models
# ============================================================

class TodoExamples(BaseModel):
    title_variants: Optional[List[str]] = None
    meta_description_variants: Optional[List[str]] = None
    h2_outline: Optional[List[str]] = None
    faq_questions: Optional[List[str]] = None
    outreach_message_draft_jp: Optional[str] = None


class Todo(BaseModel):
    todo_id: str
    priority: TodoPriority
    category: TodoCategory
    title: str
    details: str
    evidence: List[str] = []
    impact: TodoImpact
    effort: TodoEffort
    examples: Optional[TodoExamples] = None


# ============================================================
# AI Prompt Payload Models
# ============================================================

class AIConstraints(BaseModel):
    must_cite_evidence: bool = True
    no_guessing: bool = True
    max_todos_per_priority: int = 5


class AIPayloadData(BaseModel):
    summary: str
    pages: List[Dict[str, Any]]
    comparisons: List[Dict[str, Any]]
    diagnosis: Dict[str, Any]
    todos: List[Dict[str, Any]]


class AIPromptPayload(BaseModel):
    report_language: str = "ja"
    report_style: str = "consultant"
    constraints: AIConstraints = Field(default_factory=AIConstraints)
    data: AIPayloadData


# ============================================================
# Input Parameters
# ============================================================

class TimeWindows(BaseModel):
    short: int = 7
    long: int = 28


class InputParams(BaseModel):
    target_country: str = "JP"
    locale: str = "ja-JP"
    device: DeviceType = DeviceType.MOBILE
    time_windows_days: TimeWindows = Field(default_factory=TimeWindows)


# ============================================================
# Full Analysis Result
# ============================================================

class AnalysisResultFull(BaseModel):
    schema_version: str = "0.1"
    generated_at: datetime
    run_id: str
    inputs: InputParams
    pages: List[PageAnalysis]
    comparisons: List[Comparison]
    diagnosis: Diagnosis
    todos: List[Todo]
    ai_prompt_payload: AIPromptPayload


# ============================================================
# Analysis Result API Models
# ============================================================

class AnalysisResultListItem(BaseModel):
    result_id: UUID
    job_id: UUID
    generated_at: datetime
    diagnosis_main_cause: Optional[MainCause] = None


class AnalysisResultListResponse(BaseModel):
    items: List[AnalysisResultListItem]


class AnalysisResultResponse(BaseModel):
    result_id: UUID
    job_id: UUID
    generated_at: datetime
    analysis_json: Dict[str, Any]


class ReportResponse(BaseModel):
    result_id: UUID
    report_markdown: str


class ReportRegenerateRequest(BaseModel):
    report_style: Optional[str] = None


class ReportRegenerateResponse(BaseModel):
    ok: bool
    report_id: UUID


# ============================================================
# Health Check
# ============================================================

class HealthResponse(BaseModel):
    status: str
    time: datetime


# ============================================================
# Analysis Checklist Models (Appendix V)
# ============================================================

class AnalysisCheckItem(BaseModel):
    """Individual check item status (Appendix V)"""
    status: AnalysisCheckStatus
    notes: List[str] = []
    evidence_ids: List[str] = []


class AnalysisChecks(BaseModel):
    """Analysis checklist for tracking executed analyses (Appendix V)"""
    schema_version: str = "0.1"
    checks: Dict[str, AnalysisCheckItem] = {}


# ============================================================
# Progress Snapshot Models (Appendix AC)
# ============================================================

class ProgressSnapshotCreate(BaseModel):
    """Create a progress snapshot"""
    snapshot_type: SnapshotType
    pagespeed_score: Optional[int] = None
    intent_missing_count: Optional[int] = None
    avg_position: Optional[float] = None
    ctr: Optional[float] = None
    todo_total: Optional[int] = None
    todo_done: Optional[int] = None
    metrics_json: Optional[Dict[str, Any]] = None


class ProgressSnapshotResponse(BaseModel):
    """Progress snapshot response"""
    id: UUID
    site_id: UUID
    result_id: Optional[UUID] = None
    snapshot_type: SnapshotType
    pagespeed_score: Optional[int] = None
    intent_missing_count: Optional[int] = None
    avg_position: Optional[float] = None
    ctr: Optional[float] = None
    todo_total: Optional[int] = None
    todo_done: Optional[int] = None
    metrics_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class ProgressComparisonResponse(BaseModel):
    """Before/After progress comparison (Appendix AC)"""
    before: Optional[ProgressSnapshotResponse] = None
    after: Optional[ProgressSnapshotResponse] = None
    delta: Optional[Dict[str, Any]] = None


# ============================================================
# Time Series Models (Appendix AD, AE, AF)
# ============================================================

class SerpTimeSeriesItem(BaseModel):
    """SERP ranking time series item (Appendix AD)"""
    id: UUID
    site_id: UUID
    query: str
    position: float
    recorded_date: datetime
    url: Optional[str] = None
    device: DeviceType = DeviceType.MOBILE


class CrawlErrorTimeSeriesItem(BaseModel):
    """Crawl error time series item (Appendix AE)"""
    id: UUID
    site_id: UUID
    error_type: str
    error_count: int
    recorded_date: datetime
    sample_urls: Optional[List[str]] = None


class BacklinkTimeSeriesItem(BaseModel):
    """Backlink time series item (Appendix AF)"""
    id: UUID
    site_id: UUID
    total_backlinks: int
    referring_domains: int
    recorded_date: datetime
    new_backlinks: Optional[int] = None
    lost_backlinks: Optional[int] = None


# ============================================================
# Keyword Architecture Models (Appendix AL)
# ============================================================

class KeywordClusterCreate(BaseModel):
    """Create a keyword cluster"""
    cluster_name: str
    primary_keyword: str
    keywords: List[str] = []
    intent_type: Optional[str] = None


class KeywordClusterResponse(BaseModel):
    """Keyword cluster response"""
    id: UUID
    site_id: UUID
    cluster_name: str
    primary_keyword: str
    keywords: List[str]
    intent_type: Optional[str] = None
    created_at: datetime


class CannibalizationIssueResponse(BaseModel):
    """Cannibalization issue response (Appendix AL)"""
    id: UUID
    site_id: UUID
    query: str
    competing_urls: List[str]
    severity: str
    recommendation: Optional[str] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None


# ============================================================
# Content Draft Models (Appendix AO)
# ============================================================

class DraftSectionCreate(BaseModel):
    """Create a draft section"""
    section_type: str
    heading: str
    content: str
    sort_order: int = 0


class DraftSectionResponse(BaseModel):
    """Draft section response"""
    id: UUID
    draft_id: UUID
    section_type: str
    heading: str
    content: str
    sort_order: int
    created_at: datetime


class ContentDraftCreate(BaseModel):
    """Create a content draft"""
    page_id: UUID
    title: str
    meta_description: Optional[str] = None
    sections: List[DraftSectionCreate] = []


class ContentDraftResponse(BaseModel):
    """Content draft response"""
    id: UUID
    page_id: UUID
    title: str
    meta_description: Optional[str] = None
    status: DraftStatus
    created_at: datetime
    updated_at: datetime
    sections: List[DraftSectionResponse] = []


# ============================================================
# Extended Todo Models (Appendix T)
# ============================================================

class TodoItemCreate(BaseModel):
    """Create a todo item with extended fields (Appendix T)"""
    result_id: UUID
    priority: TodoPriority
    category: TodoCategory
    title: str
    details: Optional[str] = None
    impact: TodoImpact = TodoImpact.MEDIUM
    effort: TodoEffort = TodoEffort.MEDIUM
    source_checks: List[str] = []
    evidence_refs: List[str] = []
    detail_json: Optional[Dict[str, Any]] = None


class TodoItemUpdate(BaseModel):
    """Update a todo item"""
    status: Optional[TodoStatus] = None
    assignee: Optional[str] = None
    notes: Optional[str] = None


class TodoItemResponse(BaseModel):
    """Todo item response with extended fields (Appendix T)"""
    id: UUID
    result_id: UUID
    priority: TodoPriority
    category: TodoCategory
    title: str
    details: Optional[str] = None
    impact: TodoImpact
    effort: TodoEffort
    status: TodoStatus
    source_checks: List[str]
    evidence_refs: List[str]
    detail_json: Optional[Dict[str, Any]] = None
    assignee: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class TodoListResponse(BaseModel):
    """Todo list response"""
    items: List[TodoItemResponse]
    total: int
    by_priority: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
