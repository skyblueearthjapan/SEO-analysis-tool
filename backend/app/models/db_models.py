"""
SQLAlchemy database models
Based on spec.md Appendix C DB Schema
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Site(Base):
    """Sites table - プロジェクト単位"""
    __tablename__ = "sites"

    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    pages: Mapped[list["Page"]] = relationship(
        "Page",
        back_populates="site",
        cascade="all, delete-orphan"
    )
    jobs: Mapped[list["AnalysisJob"]] = relationship(
        "AnalysisJob",
        back_populates="site",
        cascade="all, delete-orphan"
    )
    results: Mapped[list["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="site",
        cascade="all, delete-orphan"
    )


class Page(Base):
    """Pages table - 分析対象URL"""
    __tablename__ = "pages"

    page_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    page_type: Mapped[str] = mapped_column(
        Text,
        CheckConstraint(
            "page_type IN ('official_homepage', 'competitor_page', 'third_party_profile_page')"
        ),
        nullable=False
    )
    label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="pages")
    job_targets: Mapped[list["AnalysisJobTarget"]] = relationship(
        "AnalysisJobTarget",
        back_populates="page",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("site_id", "url", name="uq_pages_site_url"),
    )


class AnalysisJob(Base):
    """Analysis Jobs table - 1回の実行単位"""
    __tablename__ = "analysis_jobs"

    job_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )

    # Execution parameters
    device: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("device IN ('mobile', 'desktop')"),
        default="mobile",
        nullable=False
    )
    locale: Mapped[str] = mapped_column(Text, default="ja-JP", nullable=False)
    target_country: Mapped[str] = mapped_column(Text, default="JP", nullable=False)
    enable_pagespeed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_gsc: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_ai_report: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Search Console
    gsc_property: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    brand_terms: Mapped[Optional[list]] = mapped_column(ARRAY(Text), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("status IN ('queued', 'running', 'done', 'failed')"),
        default="queued",
        nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="jobs")
    targets: Mapped[list["AnalysisJobTarget"]] = relationship(
        "AnalysisJobTarget",
        back_populates="job",
        cascade="all, delete-orphan"
    )
    results: Mapped[list["AnalysisResult"]] = relationship(
        "AnalysisResult",
        back_populates="job",
        cascade="all, delete-orphan"
    )
    reports: Mapped[list["AIReport"]] = relationship(
        "AIReport",
        back_populates="job",
        cascade="all, delete-orphan"
    )


class AnalysisJobTarget(Base):
    """Analysis Job Targets table - ジョブごとの対象ページ"""
    __tablename__ = "analysis_job_targets"

    job_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"),
        primary_key=True
    )
    page_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pages.page_id", ondelete="CASCADE"),
        primary_key=True
    )
    role: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("role IN ('official', 'competitor', 'third_party')"),
        nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="targets")
    page: Mapped["Page"] = relationship("Page", back_populates="job_targets")


class AnalysisResult(Base):
    """Analysis Results table - analysis_result.json本体"""
    __tablename__ = "analysis_results"

    result_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    job_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"),
        nullable=False
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )

    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Full analysis result as JSONB
    analysis_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Redundant storage for querying
    diagnosis_main_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="results")
    site: Mapped["Site"] = relationship("Site", back_populates="results")
    reports: Mapped[list["AIReport"]] = relationship(
        "AIReport",
        back_populates="result",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_analysis_results_site_time", "site_id", "generated_at"),
    )


class AIReport(Base):
    """AI Reports table - report.md"""
    __tablename__ = "ai_reports"

    report_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    result_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_results.result_id", ondelete="CASCADE"),
        nullable=False
    )
    job_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.job_id", ondelete="CASCADE"),
        nullable=False
    )

    report_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    result: Mapped["AnalysisResult"] = relationship("AnalysisResult", back_populates="reports")
    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="reports")


class DailyMetric(Base):
    """Daily Metrics table - 日次メトリクス（将来拡張）"""
    __tablename__ = "daily_metrics"

    metric_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    page_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pages.page_id", ondelete="CASCADE"),
        nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    source: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("source IN ('gsc', 'serp', 'manual')"),
        default="gsc",
        nullable=False
    )
    metrics_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("page_id", "date", "source", name="uq_daily_metrics_page_date_source"),
    )


# ============================================================
# Progress Tracking Tables (Appendix AC, AD, AE, AF)
# ============================================================

class ProgressSnapshot(Base):
    """Progress Snapshots table - Before/After比較用スナップショット (Appendix AC)"""
    __tablename__ = "progress_snapshots"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )
    result_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_results.result_id", ondelete="SET NULL"),
        nullable=True
    )
    snapshot_type: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("snapshot_type IN ('before', 'after', 'periodic')"),
        nullable=False
    )

    # Aggregated metrics
    pagespeed_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    intent_missing_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    avg_position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # GSC average position
    ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # GSC CTR
    todo_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    todo_done: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Additional metrics as JSONB for flexibility
    metrics_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        Index("idx_progress_snapshots_site", "site_id"),
        Index("idx_progress_snapshots_created", "site_id", "created_at"),
    )


class SerpTimeSeries(Base):
    """SERP Time Series table - GSC順位推移 (Appendix AD)"""
    __tablename__ = "serp_time_series"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)

    # GSC metrics
    impressions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clicks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("site_id", "url", "date", name="uq_serp_ts_site_url_date"),
        Index("idx_serp_ts_site", "site_id"),
        Index("idx_serp_ts_date", "date"),
    )


class CrawlErrorTimeSeries(Base):
    """Crawl Error Time Series table - クロールエラー推移 (Appendix AE)"""
    __tablename__ = "crawl_error_time_series"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )
    date: Mapped[datetime] = mapped_column(Date, nullable=False)

    # Error counts
    errors_4xx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_5xx: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Source of data
    source: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("source IN ('gsc', 'internal_crawl', 'manual')"),
        default="gsc",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("site_id", "date", "source", name="uq_crawl_error_ts_site_date_source"),
        Index("idx_crawl_error_ts_site", "site_id"),
        Index("idx_crawl_error_ts_date", "date"),
    )


class BacklinkTimeSeries(Base):
    """Backlink Time Series table - 被リンク推移 (Appendix AF)"""
    __tablename__ = "backlink_time_series"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, default="moz", nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)

    # Backlink metrics
    ref_domains: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    backlinks_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dofollow_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    authority: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Domain Authority

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("site_id", "url", "provider", "date", name="uq_backlink_ts_site_url_provider_date"),
        Index("idx_backlink_ts_site", "site_id"),
        Index("idx_backlink_ts_date", "date"),
    )


# ============================================================
# Keyword Architecture Tables (Appendix AL)
# ============================================================

class KeywordCluster(Base):
    """Keyword Clusters table - キーワードクラスタ (Appendix AL)"""
    __tablename__ = "keyword_clusters"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )
    cluster_name: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("intent IN ('informational', 'commercial', 'transactional', 'navigational')"),
        default="informational",
        nullable=False
    )
    target_page: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("status IN ('unassigned', 'partial', 'assigned')"),
        default="unassigned",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    queries: Mapped[list["ClusterQuery"]] = relationship(
        "ClusterQuery",
        back_populates="cluster",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_keyword_clusters_site", "site_id"),
    )


class ClusterQuery(Base):
    """Cluster Queries table - クラスタに含まれるクエリ (Appendix AL)"""
    __tablename__ = "cluster_queries"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    cluster_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keyword_clusters.id", ondelete="CASCADE"),
        nullable=False
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    impressions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clicks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ctr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    page: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    cluster: Mapped["KeywordCluster"] = relationship("KeywordCluster", back_populates="queries")

    __table_args__ = (
        Index("idx_cluster_queries_cluster", "cluster_id"),
    )


class CannibalizationIssue(Base):
    """Cannibalization Issues table - カニバリ検出結果 (Appendix AL)"""
    __tablename__ = "cannibalization_issues"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    pages: Mapped[dict] = mapped_column(JSONB, nullable=False)  # [{"page": "...", "position": N}]
    severity: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("severity IN ('critical', 'warning', 'info')"),
        default="warning",
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("status IN ('open', 'resolved', 'ignored')"),
        default="open",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    __table_args__ = (
        Index("idx_cannibalization_site", "site_id"),
    )


# ============================================================
# Content Draft Tables (Appendix AO)
# ============================================================

class ContentDraft(Base):
    """Content Drafts table - コンテンツドラフト (Appendix AO)"""
    __tablename__ = "content_drafts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )
    cluster_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("keyword_clusters.id", ondelete="SET NULL"),
        nullable=True
    )
    page_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    sections: Mapped[list["DraftSection"]] = relationship(
        "DraftSection",
        back_populates="draft",
        cascade="all, delete-orphan"
    )


class DraftSection(Base):
    """Draft Sections table - ドラフトセクション (Appendix AO)"""
    __tablename__ = "draft_sections"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    draft_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_drafts.id", ondelete="CASCADE"),
        nullable=False
    )
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    h2_text: Mapped[str] = mapped_column(Text, nullable=False)
    purpose: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # ["purpose1", "purpose2"]
    topics: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # ["topic1", "topic2"]
    competitor_diff: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    draft_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("status IN ('generated', 'edited', 'approved')"),
        default="generated",
        nullable=False
    )
    edited_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    edited_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    draft: Mapped["ContentDraft"] = relationship("ContentDraft", back_populates="sections")

    __table_args__ = (
        Index("idx_draft_sections_draft", "draft_id"),
    )


# ============================================================
# ToDo Extension (Appendix T)
# ============================================================

class TodoItem(Base):
    """ToDo Items table - ToDoアイテム永続化 (Appendix T)"""
    __tablename__ = "todo_items"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    site_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.site_id", ondelete="CASCADE"),
        nullable=False
    )
    result_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_results.result_id", ondelete="SET NULL"),
        nullable=True
    )

    # ToDo content
    todo_id: Mapped[str] = mapped_column(Text, nullable=False)  # Original todo_id from analysis
    priority: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("priority IN ('P0', 'P1', 'P2')"),
        nullable=False
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source tracking (Appendix V)
    source_checks: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # ["check1", "check2"]

    # Detail drawer content (Appendix T)
    detail: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # Full detail object

    # Status tracking
    status: Mapped[str] = mapped_column(
        Text,
        CheckConstraint("status IN ('open', 'in_progress', 'done', 'wont_do')"),
        default="open",
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    __table_args__ = (
        Index("idx_todo_items_site", "site_id"),
        Index("idx_todo_items_status", "site_id", "status"),
    )
