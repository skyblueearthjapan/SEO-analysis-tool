"""
Tests for Sites API
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_site(client: AsyncClient, sample_site_data: dict):
    """Test creating a new site"""
    response = await client.post("/api/v1/sites/", json=sample_site_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == sample_site_data["name"]
    assert "site_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_sites(client: AsyncClient, sample_site_data: dict):
    """Test listing sites"""
    # Create a site first
    await client.post("/api/v1/sites/", json=sample_site_data)

    # List sites
    response = await client.get("/api/v1/sites/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_site(client: AsyncClient, sample_site_data: dict):
    """Test getting a specific site"""
    # Create a site first
    create_response = await client.post("/api/v1/sites/", json=sample_site_data)
    site_id = create_response.json()["site_id"]

    # Get site
    response = await client.get(f"/api/v1/sites/{site_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["site_id"] == site_id
    assert data["name"] == sample_site_data["name"]


@pytest.mark.asyncio
async def test_get_site_not_found(client: AsyncClient):
    """Test getting a non-existent site"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/sites/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_site(client: AsyncClient, sample_site_data: dict):
    """Test deleting a site"""
    # Create a site first
    create_response = await client.post("/api/v1/sites/", json=sample_site_data)
    site_id = create_response.json()["site_id"]

    # Delete site
    response = await client.delete(f"/api/v1/sites/{site_id}")
    assert response.status_code == 204

    # Verify deletion
    get_response = await client.get(f"/api/v1/sites/{site_id}")
    assert get_response.status_code == 404
