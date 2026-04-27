from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock, patch

from mobilityradar.collectors.citybikes_collector import collect_citybikes
from mobilityradar.models import Source


def test_collect_citybikes_builds_station_availability_snapshots() -> None:
    source = Source(
        name="서울 따릉이",
        type="citybikes",
        url="https://api.citybik.es/v2/networks/seoul-bike",
        config={"limit": 2},
    )
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "network": {
            "id": "seoul-bike",
            "name": "Seoul Bike 따릉이",
            "location": {"city": "Seoul", "country": "KR"},
            "stations": [
                {
                    "id": "station-1",
                    "name": "101. Test Station",
                    "free_bikes": 3,
                    "empty_slots": 7,
                    "timestamp": "2026-04-13T00:01:02Z",
                },
                {
                    "id": "station-2",
                    "name": "102. Second Station",
                    "free_bikes": 0,
                    "empty_slots": 5,
                    "timestamp": "2026-04-13T00:02:03Z",
                },
                {
                    "id": "station-3",
                    "name": "103. Over Limit Station",
                    "free_bikes": 1,
                    "empty_slots": 1,
                    "timestamp": "2026-04-13T00:03:04Z",
                },
            ],
        }
    }

    with patch(
        "mobilityradar.collectors.citybikes_collector.requests.get",
        return_value=response,
    ) as mock_get:
        articles = collect_citybikes(source, category="mobility", limit=10, timeout=8)

    assert len(articles) == 2
    assert articles[0].title == "101. Test Station station availability - Seoul Bike 따릉이"
    assert articles[0].published == datetime(2026, 4, 13, 0, 1, 2, tzinfo=UTC)
    assert "Station ID: station-1." in articles[0].summary
    assert "Availability status: bikes_and_docks_available." in articles[0].summary
    assert articles[1].source == "서울 따릉이"
    mock_get.assert_called_once_with(
        "https://api.citybik.es/v2/networks/seoul-bike",
        timeout=20,
        headers={
            "User-Agent": "MobilityRadar/1.0 (+https://github.com/zzragida/ai-frendly-datahub)"
        },
    )
