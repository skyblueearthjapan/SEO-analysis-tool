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
