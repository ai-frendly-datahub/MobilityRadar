from __future__ import annotations

from importlib import import_module


def test_collect_browser_sources_forwards_source_config(monkeypatch) -> None:
    module = import_module("mobilityradar.browser_collector")
    source = import_module("mobilityradar.models").Source(
        name="서울 따릉이",
        type="javascript",
        url="https://www.ddareungi.seoul.kr/station",
        config={"wait_for": ".station_list", "domain_scope": "mobility"},
    )
    captured: dict[str, object] = {}

    def fake_collect(*, sources, category, timeout, health_db_path):
        captured["sources"] = sources
        captured["category"] = category
        return [], []

    monkeypatch.setattr(module, "_BROWSER_COLLECTION_AVAILABLE", True)
    monkeypatch.setattr(module, "_core_collect", fake_collect)

    articles, errors = module.collect_browser_sources([source], "mobility")

    assert articles == []
    assert errors == []
    assert captured["category"] == "mobility"
    assert captured["sources"] == [
        {
            "name": "서울 따릉이",
            "type": "javascript",
            "url": "https://www.ddareungi.seoul.kr/station",
            "config": {"wait_for": ".station_list", "domain_scope": "mobility"},
        }
    ]
