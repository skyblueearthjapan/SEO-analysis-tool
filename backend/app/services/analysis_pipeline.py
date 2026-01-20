"""
Analysis Pipeline - メイン解析パイプライン
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import get_thresholds
from app.models.db_models import (
    AIReport,
    AnalysisJob,
    AnalysisJobTarget,
    AnalysisResult,
    Page,
)
from app.services.ai_reporter import build_ai_prompt_payload, generate_report_md
from app.services.comparator import build_comparisons
from app.services.fetcher import compute_mobile_hint, http_fetch
from app.services.gsc_client import (
    classify_query_intents,
    compute_brand_summary,
    gsc_fetch_url_metrics,
)
from app.services.intent_classifier import compute_intent_coverage
from app.services.pagespeed_client import pagespeed_fetch
from app.services.parser_html import parse_html
from app.services.parser_schema import extract_structured_data
from app.services.rule_engine import run_rule_engine


async def run_analysis_job(job_id: UUID, db_url: str):
    """
    Main entry point for analysis job execution

    Args:
        job_id: Job UUID
        db_url: Database connection URL
    """
    # Create new engine and session for background task
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        try:
            # Load job with targets
            result = await db.execute(
                select(AnalysisJob)
                .options(selectinload(AnalysisJob.targets))
                .where(AnalysisJob.job_id == job_id)
            )
            job = result.scalar_one_or_none()

            if job is None:
                print(f"Job not found: {job_id}")
                return

            # Update status to running
            job.status = "running"
            job.started_at = datetime.utcnow()
            await db.commit()

            # Load configuration
            cfg = get_thresholds()

            # Load pages
            page_ids = [t.page_id for t in job.targets]
            pages_result = await db.execute(
                select(Page).where(Page.page_id.in_(page_ids))
            )
            pages_db = {p.page_id: p for p in pages_result.scalars().all()}

            # Build target info with page data
            targets = []
            for target in job.targets:
                page = pages_db.get(target.page_id)
                if page:
                    targets.append({
                        "page_id": str(page.page_id),
                        "url": page.url,
                        "page_type": page.page_type,
                        "role": target.role
                    })

            # Run analysis
            analysis_result = await _run_analysis(
                job=job,
                targets=targets,
                cfg=cfg
            )

            # Save result
            result_record = AnalysisResult(
                job_id=job.job_id,
                site_id=job.site_id,
                schema_version=analysis_result["schema_version"],
                generated_at=datetime.fromisoformat(
                    analysis_result["generated_at"].replace("Z", "+00:00")
                ),
                analysis_json=analysis_result,
                diagnosis_main_cause=analysis_result["diagnosis"]["main_cause"]
            )
            db.add(result_record)
            await db.flush()

            # Generate AI report if enabled
            if job.enable_ai_report:
                ai_payload = analysis_result["ai_prompt_payload"]
                report_md = await generate_report_md(ai_payload, cfg)

                report_record = AIReport(
                    result_id=result_record.result_id,
                    job_id=job.job_id,
                    report_markdown=report_md,
                    model_name="gpt-4o",
                    prompt_version="1.0"
                )
                db.add(report_record)

            # Update job status
            job.status = "done"
            job.finished_at = datetime.utcnow()
            await db.commit()

            print(f"Analysis job completed: {job_id}")

        except Exception as e:
            # Update job status to failed
            try:
                job.status = "failed"
                job.error_message = str(e)[:1000]
                job.finished_at = datetime.utcnow()
                await db.commit()
            except Exception:
                pass

            print(f"Analysis job failed: {job_id} - {e}")
            raise

        finally:
            await engine.dispose()


async def _run_analysis(
    job: AnalysisJob,
    targets: List[Dict[str, Any]],
    cfg: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Run the full analysis pipeline

    Args:
        job: Analysis job record
        targets: List of target page info
        cfg: Configuration dictionary

    Returns:
        Complete analysis result dictionary
    """
    from app.config import get_settings
    settings = get_settings()

    # Analyze each page
    pages = []
    for target in targets:
        page_result = await _analyze_single_page(
            target=target,
            job=job,
            cfg=cfg,
            settings=settings
        )
        pages.append(page_result)

    # Build comparisons
    comparisons = build_comparisons(pages, cfg)

    # Run rule engine
    diagnosis, todos = run_rule_engine(pages, comparisons, cfg)

    # Build AI prompt payload
    ai_payload = build_ai_prompt_payload(pages, comparisons, diagnosis, todos, cfg)

    # Build inputs
    inputs = {
        "target_country": job.target_country,
        "locale": job.locale,
        "device": job.device,
        "time_windows_days": {
            "short": cfg.get("app", {}).get("time_windows_days", {}).get("short", 7),
            "long": cfg.get("app", {}).get("time_windows_days", {}).get("long", 28)
        }
    }

    # Assemble final result
    return {
        "schema_version": cfg.get("app", {}).get("schema_version", "0.1"),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "run_id": str(job.job_id),
        "inputs": inputs,
        "pages": pages,
        "comparisons": comparisons,
        "diagnosis": diagnosis,
        "todos": todos,
        "ai_prompt_payload": ai_payload
    }


async def _analyze_single_page(
    target: Dict[str, Any],
    job: AnalysisJob,
    cfg: Dict[str, Any],
    settings: Any
) -> Dict[str, Any]:
    """
    Analyze a single page

    Args:
        target: Target page info
        job: Analysis job
        cfg: Configuration
        settings: Application settings

    Returns:
        Page analysis dictionary
    """
    url = target["url"]
    page_type = target["page_type"]
    page_id = target["page_id"]

    # Fetch page
    fetch_result = await http_fetch(url)

    # Parse HTML
    html_analysis = parse_html(fetch_result.html, fetch_result.final_url)

    # Extract structured data
    schema_data = extract_structured_data(fetch_result.html)

    # Compute mobile hint
    mobile_hint = compute_mobile_hint(fetch_result.html, cfg)

    # PageSpeed (if enabled)
    pagespeed_result = {
        "available": False,
        "performance_score": None,
        "lcp_ms": None,
        "inp_ms": None,
        "cls": None
    }
    if job.enable_pagespeed:
        ps = await pagespeed_fetch(
            url=fetch_result.final_url,
            device=job.device,
            api_key=settings.pagespeed_api_key
        )
        pagespeed_result = {
            "available": ps.available,
            "performance_score": ps.performance_score,
            "lcp_ms": ps.lcp_ms,
            "inp_ms": ps.inp_ms,
            "cls": ps.cls
        }

    # Search Console (only for official pages)
    gsc_result = {
        "available": False,
        "time_window_days": None,
        "top_queries": [],
        "brand_query_summary": {
            "brand_queries_present": False,
            "brand_impressions": 0,
            "brand_ctr": 0.0
        }
    }
    if page_type == "official_homepage" and job.enable_gsc and job.gsc_property:
        gsc = await gsc_fetch_url_metrics(
            site_property=job.gsc_property,
            url=fetch_result.final_url,
            days=cfg.get("app", {}).get("time_windows_days", {}).get("long", 28),
            max_queries=cfg.get("app", {}).get("max_queries_per_url", 20),
            credentials_path=settings.gsc_credentials_path
        )
        if gsc.available:
            # Classify query intents
            queries = classify_query_intents(gsc.top_queries, job.brand_terms)
            brand_summary = compute_brand_summary(queries, job.brand_terms)

            gsc_result = {
                "available": True,
                "time_window_days": gsc.time_window_days,
                "top_queries": [
                    {
                        "query": q.query,
                        "impressions": q.impressions,
                        "clicks": q.clicks,
                        "ctr": q.ctr,
                        "position": q.position,
                        "query_intent": q.query_intent
                    }
                    for q in queries
                ],
                "brand_query_summary": {
                    "brand_queries_present": brand_summary.brand_queries_present,
                    "brand_impressions": brand_summary.brand_impressions,
                    "brand_ctr": brand_summary.brand_ctr
                }
            }

    # Intent coverage
    intent_result = compute_intent_coverage(
        page_type=page_type,
        title=html_analysis.title,
        h2_list=html_analysis.headings.get("h2", []),
        text=html_analysis.full_text,
        links=html_analysis.links,
        brand_terms=job.brand_terms,
        cfg=cfg
    )

    # Build page analysis result
    return {
        "page_id": page_id,
        "url": url,
        "page_type": page_type,
        "fetch": {
            "status_code": fetch_result.status_code,
            "final_url": fetch_result.final_url,
            "redirect_chain": fetch_result.redirect_chain
        },
        "html": {
            "title": html_analysis.title,
            "meta_description": html_analysis.meta_description,
            "canonical": html_analysis.canonical,
            "robots_meta": html_analysis.robots_meta,
            "headings": html_analysis.headings,
            "text_stats": html_analysis.text_stats,
            "links": html_analysis.links,
            "images": html_analysis.images,
            "structured_data": {
                "types": schema_data.types,
                "has_faq_schema": schema_data.has_faq_schema,
                "has_organization_schema": schema_data.has_organization_schema,
                "has_article_schema": schema_data.has_article_schema
            }
        },
        "tech": {
            "mobile_friendly_hint": mobile_hint,
            "pagespeed": pagespeed_result
        },
        "content": {
            "intent_coverage": intent_result.intent_coverage,
            "missing_sections": intent_result.missing_sections,
            "notes": intent_result.notes
        },
        "serp": {
            "available": False,
            "queries_tested": [],
            "serp_features": [],
            "top_results": []
        },
        "search_console": gsc_result
    }
