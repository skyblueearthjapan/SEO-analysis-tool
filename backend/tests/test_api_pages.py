"""
Tests for Pages API
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_page(
    client: AsyncClient, sample_site_data: dict, sample_page_data: dict
):
    """Test creating a new page"""
    # Create a site first
    site_response = await client.post("/api/v1/sites/", json=sample_site_data)
    site_id = site_response.json()["site_id"]

    # Create page
    response = await client.post(
        f"/api/v1/sites/{site_id}/pages/", json=sample_page_data
    )
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == sample_page_data["url"]
    assert data["page_type"] == sample_page_data["page_type"]
    assert "page_id" in data


@pytest.mark.asyncio
async def test_create_page_invalid_url(
    client: AsyncClient, sample_site_data: dict
):
    """Test creating a page with invalid URL"""
    # Create a site first
    site_response = await client.post("/api/v1/sites/", json=sample_site_data)
    site_id = site_response.json()["site_id"]

    # Try to create page with invalid URL
    response = await client.post(
        f"/api/v1/sites/{site_id}/pages/",
        json={
            "url": "not-a-valid-url",
            "page_type": "official_homepage",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_pages(
    client: AsyncClient, sample_site_data: dict, sample_page_data: dict
):
    """Test listing pages"""
    # Create a site and page
    site_response = await client.post("/api/v1/sites/", json=sample_site_data)
    site_id = site_response.json()["site_id"]
    await client.post(f"/api/v1/sites/{site_id}/pages/", json=sample_page_data)

    # List pages
    response = await client.get(f"/api/v1/sites/{site_id}/pages/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_list_pages_by_type(
    client: AsyncClient, sample_site_data: dict, sample_page_data: dict
):
    """Test listing pages filtered by type"""
    # Create a site and page
    site_response = await client.post("/api/v1/sites/", json=sample_site_data)
    site_id = site_response.json()["site_id"]
    await client.post(f"/api/v1/sites/{site_id}/pages/", json=sample_page_data)

    # List pages by type
    response = await client.get(
        f"/api/v1/sites/{site_id}/pages/?page_type=official_homepage"
    )
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["page_type"] == "official_homepage"


@pytest.mark.asyncio
async def test_get_page(
    client: AsyncClient, sample_site_data: dict, sample_page_data: dict
):
    """Test getting a specific page"""
    # Create site and page
    site_response = await client.post("/api/v1/sites/", json=sample_site_data)
    site_id = site_response.json()["site_id"]
    page_response = await client.post(
        f"/api/v1/sites/{site_id}/pages/", json=sample_page_data
    )
    page_id = page_response.json()["page_id"]

    # Get page
    response = await client.get(f"/api/v1/sites/{site_id}/pages/{page_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["page_id"] == page_id


@pytest.mark.asyncio
async def test_delete_page(
    client: AsyncClient, sample_site_data: dict, sample_page_data: dict
):
    """Test deleting a page"""
    # Create site and page
    site_response = await client.post("/api/v1/sites/", json=sample_site_data)
    site_id = site_response.json()["site_id"]
    page_response = await client.post(
        f"/api/v1/sites/{site_id}/pages/", json=sample_page_data
    )
    page_id = page_response.json()["page_id"]

    # Delete page
    response = await client.delete(f"/api/v1/sites/{site_id}/pages/{page_id}")
    assert response.status_code == 204

    # Verify deletion
    get_response = await client.get(f"/api/v1/sites/{site_id}/pages/{page_id}")
    assert get_response.status_code == 404
