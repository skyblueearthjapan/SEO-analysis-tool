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
    DateTime,
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
