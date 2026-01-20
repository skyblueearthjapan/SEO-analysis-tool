"""
Structured Data Parser - JSON-LD構造化データ抽出
"""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

from bs4 import BeautifulSoup


@dataclass
class StructuredDataResult:
    """Structured data extraction result"""
    types: List[str] = field(default_factory=list)
    has_faq_schema: bool = False
    has_organization_schema: bool = False
    has_article_schema: bool = False
    has_website_schema: bool = False
    has_breadcrumb_schema: bool = False
    has_local_business_schema: bool = False
    raw_data: List[Dict[str, Any]] = field(default_factory=list)


def extract_structured_data(html: str) -> StructuredDataResult:
    """
    Extract JSON-LD structured data from HTML

    Args:
        html: HTML content string

    Returns:
        StructuredDataResult with extracted schema information
    """
    if not html:
        return StructuredDataResult()

    soup = BeautifulSoup(html, 'lxml')
    scripts = soup.find_all('script', type='application/ld+json')

    types: List[str] = []
    raw_data: List[Dict[str, Any]] = []

    for script in scripts:
        if not script.string:
            continue

        try:
            data = json.loads(script.string)

            # Handle @graph structure
            if isinstance(data, dict) and '@graph' in data:
                items = data['@graph']
            elif isinstance(data, list):
                items = data
            else:
                items = [data]

            for item in items:
                if not isinstance(item, dict):
                    continue

                raw_data.append(item)

                # Extract @type
                schema_type = item.get('@type', '')
                if isinstance(schema_type, list):
                    types.extend(schema_type)
                elif schema_type:
                    types.append(schema_type)

        except json.JSONDecodeError:
            continue
        except Exception:
            continue

    # Check for specific schema types
    types_lower = [t.lower() for t in types]

    has_faq = any(t in ['faqpage', 'faq'] for t in types_lower)
    has_organization = any(t in ['organization', 'localorganization'] for t in types_lower)
    has_article = any(t in ['article', 'newsarticle', 'blogposting'] for t in types_lower)
    has_website = any(t in ['website'] for t in types_lower)
    has_breadcrumb = any(t in ['breadcrumblist'] for t in types_lower)
    has_local_business = any(
        t in ['localbusiness', 'restaurant', 'hotel', 'store', 'medicalorganization']
        for t in types_lower
    )

    return StructuredDataResult(
        types=list(set(types)),  # Remove duplicates
        has_faq_schema=has_faq,
        has_organization_schema=has_organization,
        has_article_schema=has_article,
        has_website_schema=has_website,
        has_breadcrumb_schema=has_breadcrumb,
        has_local_business_schema=has_local_business,
        raw_data=raw_data
    )
