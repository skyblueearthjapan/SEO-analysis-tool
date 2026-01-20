"""
Sites router - プロジェクト管理API
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import Site
from app.models.schemas import SiteCreate, SiteListResponse, SiteResponse

router = APIRouter()


@router.post("", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
async def create_site(
    site_in: SiteCreate,
    db: AsyncSession = Depends(get_db)
) -> SiteResponse:
    """Create a new site/project"""
    site = Site(name=site_in.name)
    db.add(site)
    await db.flush()
    await db.refresh(site)

    return SiteResponse(
        site_id=site.site_id,
        name=site.name,
        created_at=site.created_at
    )


@router.get("", response_model=SiteListResponse)
async def list_sites(
    db: AsyncSession = Depends(get_db)
) -> SiteListResponse:
    """List all sites"""
    result = await db.execute(
        select(Site).order_by(Site.created_at.desc())
    )
    sites = result.scalars().all()

    return SiteListResponse(
        items=[
            SiteResponse(
                site_id=site.site_id,
                name=site.name,
                created_at=site.created_at
            )
            for site in sites
        ]
    )


@router.get("/{site_id}", response_model=SiteResponse)
async def get_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> SiteResponse:
    """Get a single site by ID"""
    result = await db.execute(
        select(Site).where(Site.site_id == site_id)
    )
    site = result.scalar_one_or_none()

    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}"
        )

    return SiteResponse(
        site_id=site.site_id,
        name=site.name,
        created_at=site.created_at
    )


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_site(
    site_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a site and all related data"""
    result = await db.execute(
        select(Site).where(Site.site_id == site_id)
    )
    site = result.scalar_one_or_none()

    if site is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Site not found: {site_id}"
        )

    await db.delete(site)
    return None
