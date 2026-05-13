from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from radar_core.report_utils import (
    generate_index_html as _core_generate_index_html,
)
from radar_core.report_utils import (
    generate_report as _core_generate_report,
)

from .models import Article, CategoryConfig


# Map shortened / colloquial region names to their canonical 시도 form.
_REGION_CANONICAL = {
    "서울": "서울특별시",
    "서울시": "서울특별시",
    "seoul": "서울특별시",
    "부산": "부산광역시",
    "부산시": "부산광역시",
    "busan": "부산광역시",
    "대구": "대구광역시",
    "대구시": "대구광역시",
    "인천": "인천광역시",
    "인천시": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "경기도": "경기도",
    "강원": "강원특별자치도",
    "강원도": "강원특별자치도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전북특별자치도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}

_REGION_ENTITY_KEYS = {"city", "region", "regions", "도시", "지역"}


def _build_regional_section(
    entities_json_rows: Iterable[object],
) -> dict[str, object] | None:
    """Aggregate city/region mentions and render a coverage table section."""
    counter: Counter[str] = Counter()
    for row in entities_json_rows or []:
        if isinstance(row, str):
            try:
                row = json.loads(row)
            except json.JSONDecodeError:
                continue
        if not isinstance(row, dict):
            continue
        for key, raw_values in row.items():
            if key not in _REGION_ENTITY_KEYS:
                continue
            if isinstance(raw_values, str):
                values = [raw_values]
            elif isinstance(raw_values, list):
                values = [v for v in raw_values if isinstance(v, str)]
            else:
                continue
            for value in values:
                canonical = _REGION_CANONICAL.get(value.strip().lower(), value.strip())
                if canonical:
                    counter[canonical] += 1

    if not counter:
        return None

    rows = "".join(
        f"<tr><td>{region}</td><td>{count}</td></tr>"
        for region, count in counter.most_common()
    )
    body = (
        '<div class="regional-coverage-wrap">'
        '<table class="regional-coverage">'
        '<thead><tr><th>Region (시도)</th><th>Mentions</th></tr></thead>'
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</div>"
    )
    return {
        "id": "regional-availability",
        "aria_label": "Regional Mobility Availability",
        "title": "Regional Mobility Availability",
        "panel_title": "Korea Mobility Coverage",
        "subtitle": "Mention counts per Korean 시도 across collected articles",
        "badges": [],
        "body_html": body,
    }


def generate_report(
    *,
    category: CategoryConfig,
    articles: Iterable[Article],
    output_path: Path,
    stats: dict[str, int],
    errors: list[str] | None = None,
    store=None,
    entities_json_rows: list[dict[str, object]] | None = None,
) -> Path:
    """Generate HTML report (delegates to radar-core)."""
    articles_list = list(articles)
    plugin_charts = []

    # --- Universal plugins (entity heatmap + source reliability) ---
    try:
        from radar_core.plugins.entity_heatmap import get_chart_config as _heatmap_config

        _heatmap = _heatmap_config(articles=articles_list)
        if _heatmap is not None:
            plugin_charts.append(_heatmap)
    except Exception:
        pass
    try:
        from radar_core.plugins.source_reliability import get_chart_config as _reliability_config

        _reliability = _reliability_config(store=store)
        if _reliability is not None:
            plugin_charts.append(_reliability)
    except Exception:
        pass

    extra_sections: list[dict[str, object]] = []
    regional_section = _build_regional_section(entities_json_rows or [])
    if regional_section is not None:
        extra_sections.append(regional_section)

    return _core_generate_report(
        category=category,
        articles=articles_list,
        output_path=output_path,
        stats=stats,
        errors=errors,
        plugin_charts=plugin_charts if plugin_charts else None,
        extra_sections=extra_sections if extra_sections else None,
    )


def generate_index_html(
    report_dir: Path,
    summaries_dir: Path | None = None,
) -> Path:
    """Generate index.html (delegates to radar-core)."""
    radar_name = "Mobility Radar"
    return _core_generate_index_html(report_dir, radar_name)
