"""
Pages router - URL管理API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Page, Site
from app.models.schemas import (
    PageCreate,
    PageDeleteResponse,
    PageListResponse,
    PageResponse,
    PageUpdate,
)

router = APIRouter()


async def get_site_or_404(db: AsyncSession, site_id: UUID) -> Site:
    """Helper to get site or raise 404"""
    result = await db.execute(
        select(Site).where(Site.site_id == site_id)
    )
    site = result.scalar_one_or_none()
    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}"
        )
    return site


@router.post("", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
async def create_page(
    site_id: UUID,
    page_in: PageCreate,
    db: AsyncSession = Depends(get_db)
) -> PageResponse:
    """Register a new URL with page type"""
    await get_site_or_404(db, site_id)

    # Check for duplicate URL in same site
    existing = await db.execute(
        select(Page).where(
            Page.site_id == site_id,
            Page.url == page_in.url
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"URL already exists for this site: {page_in.url}"
        )

    page = Page(
        site_id=site_id,
        url=page_in.url,
        page_type=page_in.page_type.value,
        label=page_in.label
    )
    db.add(page)
    await db.flush()
    await db.refresh(page)

    return PageResponse(
        page_id=page.page_id,
        site_id=page.site_id,
        url=page.url,
        page_type=page.page_type,
        label=page.label,
        created_at=page.created_at
    )


@router.get("", response_model=PageListResponse)
async def list_pages(
    site_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> PageListResponse:
    """List all pages for a site"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(Page)
        .where(Page.site_id == site_id)
        .order_by(Page.created_at.desc())
    )
    pages = result.scalars().all()

    return PageListResponse(
        items=[
            PageResponse(
                page_id=page.page_id,
                site_id=page.site_id,
                url=page.url,
                page_type=page.page_type,
                label=page.label,
                created_at=page.created_at
            )
            for page in pages
        ]
    )


@router.get("/{page_id}", response_model=PageResponse)
async def get_page(
    site_id: UUID,
    page_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> PageResponse:
    """Get a single page by ID"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(Page).where(
            Page.site_id == site_id,
            Page.page_id == page_id
        )
    )
    page = result.scalar_one_or_none()

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page not found: {page_id}"
        )

    return PageResponse(
        page_id=page.page_id,
        site_id=page.site_id,
        url=page.url,
        page_type=page.page_type,
        label=page.label,
        created_at=page.created_at
    )


@router.patch("/{page_id}", response_model=PageResponse)
async def update_page(
    site_id: UUID,
    page_id: UUID,
    page_in: PageUpdate,
    db: AsyncSession = Depends(get_db)
) -> PageResponse:
    """Update a page (label, page_type)"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(Page).where(
            Page.site_id == site_id,
            Page.page_id == page_id
        )
    )
    page = result.scalar_one_or_none()

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page not found: {page_id}"
        )

    # Update fields if provided
    if page_in.label is not None:
        page.label = page_in.label
    if page_in.page_type is not None:
        page.page_type = page_in.page_type.value

    await db.flush()
    await db.refresh(page)

    return PageResponse(
        page_id=page.page_id,
        site_id=page.site_id,
        url=page.url,
        page_type=page.page_type,
        label=page.label,
        created_at=page.created_at
    )


@router.delete("/{page_id}", response_model=PageDeleteResponse)
async def delete_page(
    site_id: UUID,
    page_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> PageDeleteResponse:
    """Delete a page"""
    await get_site_or_404(db, site_id)

    result = await db.execute(
        select(Page).where(
            Page.site_id == site_id,
            Page.page_id == page_id
        )
    )
    page = result.scalar_one_or_none()

    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Page not found: {page_id}"
        )

    await db.delete(page)
    return PageDeleteResponse(deleted=True)
