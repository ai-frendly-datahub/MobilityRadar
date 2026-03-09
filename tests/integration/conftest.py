from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from mobilityradar.models import Article, CategoryConfig, EntityDefinition, Source
from mobilityradar.storage import RadarStorage


@pytest.fixture
def tmp_storage(tmp_path: Path) -> RadarStorage:
    """Create a temporary RadarStorage instance for testing."""
    db_path = tmp_path / "test.duckdb"
    storage = RadarStorage(db_path)
    yield storage
    storage.close()


@pytest.fixture
def sample_articles() -> list[Article]:
    """Create sample articles with realistic mobility domain data."""
    now = datetime.now(timezone.utc)
    return [
        Article(
            title="서울 공유자전거 이용 증가 추세",
            link="https://mobility.example.com/bike-sharing-2024",
            summary="서울의 공유자전거 이용이 계속 증가하고 있습니다. 자전거 도로 확충도 진행 중입니다.",
            published=now,
            source="mobility_news",
            category="mobility",
            matched_entities={},
        ),
        Article(
            title="전기차 충전소 확대 계획 발표",
            link="https://mobility.example.com/ev-charging-2024",
            summary="정부가 전기차 충전소 확대 계획을 발표했습니다. 올해 1000개 이상 추가 설치 예정입니다.",
            published=now,
            source="mobility_news",
            category="mobility",
            matched_entities={},
        ),
        Article(
            title="킥보드 안전 규정 강화",
            link="https://mobility.example.com/kickboard-safety-2024",
            summary="킥보드 이용자 안전을 위한 규정이 강화됩니다. 헬멧 착용 의무화 등이 포함됩니다.",
            published=now,
            source="mobility_news",
            category="mobility",
            matched_entities={},
        ),
        Article(
            title="대중교통 통합 앱 출시",
            link="https://mobility.example.com/transit-app-2024",
            summary="버스, 지하철, 택시를 통합 관리하는 앱이 출시되었습니다.",
            published=now,
            source="mobility_news",
            category="mobility",
            matched_entities={},
        ),
        Article(
            title="스쿠터 공유 서비스 확대",
            link="https://mobility.example.com/scooter-sharing-2024",
            summary="스쿠터 공유 서비스가 더 많은 지역으로 확대됩니다.",
            published=now,
            source="mobility_news",
            category="mobility",
            matched_entities={},
        ),
    ]


@pytest.fixture
def sample_entities() -> list[EntityDefinition]:
    """Create sample entities with mobility domain keywords."""
    return [
        EntityDefinition(
            name="bike_sharing",
            display_name="자전거 공유",
            keywords=["자전거", "공유자전거", "자전거도로", "라이딩"],
        ),
        EntityDefinition(
            name="electric_vehicle",
            display_name="전기차",
            keywords=["전기차", "EV", "충전소", "배터리"],
        ),
        EntityDefinition(
            name="kickboard",
            display_name="킥보드",
            keywords=["킥보드", "스쿠터", "전동킥보드", "안전"],
        ),
        EntityDefinition(
            name="public_transit",
            display_name="대중교통",
            keywords=["버스", "지하철", "택시", "대중교통"],
        ),
        EntityDefinition(
            name="micro_mobility",
            display_name="마이크로 모빌리티",
            keywords=["스쿠터", "공유", "모빌리티", "이동수단"],
        ),
    ]


@pytest.fixture
def sample_config(tmp_path: Path, sample_entities: list[EntityDefinition]) -> CategoryConfig:
    """Create a sample CategoryConfig for testing."""
    sources = [
        Source(
            name="mobility_news",
            type="rss",
            url="https://mobility.example.com/feed",
        ),
    ]
    return CategoryConfig(
        category_name="mobility",
        display_name="모빌리티",
        sources=sources,
        entities=sample_entities,
    )
