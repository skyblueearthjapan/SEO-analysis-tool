"""
Tests for analysis services
"""

import pytest

from app.services.parser_html import parse_html
from app.services.parser_schema import extract_structured_data
from app.services.intent_classifier import compute_intent_coverage
from app.services.rule_engine import run_rule_engine
from app.services.comparator import build_comparisons


class TestParserHtml:
    """Tests for HTML parser"""

    def test_parse_title(self):
        """Test title extraction"""
        html = "<html><head><title>Test Title</title></head><body></body></html>"
        result = parse_html(html, "https://example.com")
        assert result.title == "Test Title"

    def test_parse_meta_description(self):
        """Test meta description extraction"""
        html = """
        <html>
        <head>
            <meta name="description" content="Test description">
        </head>
        <body></body>
        </html>
        """
        result = parse_html(html, "https://example.com")
        assert result.meta_description == "Test description"

    def test_parse_headings(self):
        """Test heading extraction"""
        html = """
        <html>
        <body>
            <h1>Main Heading</h1>
            <h2>Sub Heading 1</h2>
            <h2>Sub Heading 2</h2>
            <h3>Sub Sub Heading</h3>
        </body>
        </html>
        """
        result = parse_html(html, "https://example.com")
        assert len(result.headings["h1"]) == 1
        assert len(result.headings["h2"]) == 2
        assert len(result.headings["h3"]) == 1
        assert result.headings["h1"][0] == "Main Heading"

    def test_parse_canonical(self):
        """Test canonical URL extraction"""
        html = """
        <html>
        <head>
            <link rel="canonical" href="https://example.com/page">
        </head>
        <body></body>
        </html>
        """
        result = parse_html(html, "https://example.com")
        assert result.canonical == "https://example.com/page"

    def test_parse_links(self):
        """Test link extraction"""
        html = """
        <html>
        <body>
            <a href="https://example.com/page1">Internal</a>
            <a href="https://example.com/page2">Internal 2</a>
            <a href="https://external.com/page">External</a>
        </body>
        </html>
        """
        result = parse_html(html, "https://example.com")
        assert result.links["internal_count"] == 2
        assert result.links["external_count"] == 1

    def test_parse_images(self):
        """Test image extraction"""
        html = """
        <html>
        <body>
            <img src="img1.jpg" alt="Image 1">
            <img src="img2.jpg">
            <img src="img3.jpg" alt="">
        </body>
        </html>
        """
        result = parse_html(html, "https://example.com")
        assert result.images["total_count"] == 3
        assert result.images["without_alt_count"] == 2


class TestParserSchema:
    """Tests for schema.org parser"""

    def test_extract_organization_schema(self):
        """Test organization schema extraction"""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Test Company"
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        result = extract_structured_data(html)
        assert result.has_organization_schema is True
        assert "Organization" in result.types

    def test_extract_faq_schema(self):
        """Test FAQ schema extraction"""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": []
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        result = extract_structured_data(html)
        assert result.has_faq_schema is True

    def test_extract_multiple_schemas(self):
        """Test multiple schema extraction"""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@graph": [
                    {"@type": "Organization", "name": "Test"},
                    {"@type": "Article", "headline": "Test Article"}
                ]
            }
            </script>
        </head>
        <body></body>
        </html>
        """
        result = extract_structured_data(html)
        assert result.has_organization_schema is True
        assert result.has_article_schema is True


class TestIntentClassifier:
    """Tests for intent classifier"""

    def test_intent_coverage_official(self):
        """Test intent coverage for official homepage"""
        result = compute_intent_coverage(
            page_type="official_homepage",
            title="会社名 - 製品・サービス紹介",
            h2_list=["製品紹介", "サービス内容", "料金プラン", "会社概要", "お問い合わせ"],
            text="会社名は製品とサービスを提供しています。料金プランは月額1000円から。"
                 "会社概要や問い合わせ先もこちらから。",
            links={"internal_count": 10, "external_count": 2},
            brand_terms=["会社名"],
            cfg={}
        )
        assert result.intent_coverage > 0.0
        assert isinstance(result.missing_sections, list)

    def test_intent_coverage_third_party(self):
        """Test intent coverage for third-party page"""
        result = compute_intent_coverage(
            page_type="third_party_profile_page",
            title="会社名 - レビュー",
            h2_list=["口コミ", "評価"],
            text="会社名のレビューです。",
            links={"internal_count": 5, "external_count": 1},
            brand_terms=["会社名"],
            cfg={}
        )
        assert result.intent_coverage >= 0.0


class TestRuleEngine:
    """Tests for rule engine"""

    def test_run_rule_engine_basic(self):
        """Test basic rule engine execution"""
        pages = [
            {
                "page_id": "1",
                "page_type": "official_homepage",
                "url": "https://example.com",
                "html": {
                    "title": "Test Title - Company Name",
                    "meta_description": "This is a test meta description that is long enough.",
                    "headings": {"h1": ["Main"], "h2": ["Sub1", "Sub2"]},
                    "text_stats": {"word_count": 1000},
                    "links": {"internal_count": 10, "external_count": 2},
                    "images": {"total_count": 5, "without_alt_count": 1},
                    "structured_data": {
                        "has_organization_schema": True,
                        "has_faq_schema": False,
                    },
                },
                "tech": {
                    "pagespeed": {
                        "available": True,
                        "performance_score": 85,
                        "lcp_ms": 2000,
                        "cls": 0.05,
                    },
                },
                "content": {
                    "intent_coverage": 0.7,
                    "missing_sections": ["FAQ"],
                },
            }
        ]
        comparisons = {}
        cfg = {
            "thresholds": {
                "title_length_min": 30,
                "title_length_max": 60,
                "meta_description_length_min": 70,
                "meta_description_length_max": 155,
                "content_word_count_min": 500,
            },
            "scoring": {
                "weights": {
                    "content_quality": 0.4,
                    "technical": 0.3,
                    "authority": 0.15,
                    "ctr": 0.15,
                }
            },
        }

        diagnosis, todos = run_rule_engine(pages, comparisons, cfg)

        assert "main_cause" in diagnosis
        assert "overall_score" in diagnosis
        assert "grade" in diagnosis
        assert isinstance(todos, list)


class TestComparator:
    """Tests for comparator"""

    def test_build_comparisons(self):
        """Test comparison building"""
        pages = [
            {
                "page_type": "official_homepage",
                "html": {
                    "title": "Short Title",
                    "headings": {"h1": ["Main"], "h2": ["Sub1"]},
                    "text_stats": {"word_count": 500},
                },
            },
            {
                "page_type": "competitor_page",
                "html": {
                    "title": "Longer Competitor Title Here",
                    "headings": {"h1": ["Comp Main"], "h2": ["Sub1", "Sub2", "Sub3"]},
                    "text_stats": {"word_count": 1500},
                },
            },
        ]
        cfg = {}

        result = build_comparisons(pages, cfg)

        assert "diff_summary" in result
        assert "structure_comparison" in result
