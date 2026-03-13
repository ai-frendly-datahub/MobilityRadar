from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from jinja2 import Environment, FileSystemLoader

from .models import Article, CategoryConfig


_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,
    )


def _copy_static_assets(report_dir: Path) -> None:
    src = _TEMPLATE_DIR / "static"
    dst = report_dir / "static"
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        _ = shutil.copytree(str(src), str(dst))


def generate_report(
    *,
    category: CategoryConfig,
    articles: Iterable[Article],
    output_path: Path,
    stats: dict[str, int],
    errors: list[str] | None = None,
    entities_json_rows: Iterable[str] | None = None,
) -> Path:
    """Render a simple HTML report for the collected articles."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    articles_list = list(articles)
    entity_counts = _count_entities(articles_list)
    raw_entity_rows = list(entities_json_rows) if entities_json_rows is not None else []
    if not raw_entity_rows:
        raw_entity_rows = [
            json.dumps(article.matched_entities, ensure_ascii=False)
            for article in articles_list
            if article.matched_entities
        ]
    regional_counts = _count_sido_mentions(raw_entity_rows)
    regional_rows = sorted(regional_counts.items(), key=lambda item: (-item[1], item[0]))
    korea_map_html = _build_korea_choropleth_map_html(regional_counts)

    # Convert Article objects to dicts for JSON serialization (for JavaScript charts)
    articles_json = []
    for article in articles_list:
        article_data = {
            "title": article.title,
            "link": article.link,
            "source": article.source,
            "published": article.published.isoformat() if article.published else None,
            "published_at": article.published.isoformat() if article.published else None,
            "summary": article.summary,
            "matched_entities": article.matched_entities or {},
            "collected_at": (
                article.collected_at.isoformat()
                if hasattr(article, "collected_at") and article.collected_at
                else None
            ),
        }
        articles_json.append(article_data)

    template = _get_jinja_env().get_template("report.html")
    rendered = template.render(
        category=category,
        articles=articles_list,  # Keep original for template rendering
        articles_json=articles_json,  # JSON-serializable version for charts
        generated_at=datetime.now(UTC),
        stats=stats,
        entity_counts=entity_counts,
        regional_rows=regional_rows,
        korea_map_html=korea_map_html,
        errors=errors or [],
    )
    _ = output_path.write_text(rendered, encoding="utf-8")

    now_ts = datetime.now(UTC)
    date_stamp = now_ts.strftime("%Y%m%d")
    dated_name = f"{category.category_name}_{date_stamp}.html"
    dated_path = output_path.parent / dated_name
    _ = dated_path.write_text(rendered, encoding="utf-8")

    _copy_static_assets(output_path.parent)

    return output_path


def _count_entities(articles: Iterable[Article]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for article in articles:
        for entity_name, keywords in (article.matched_entities or {}).items():
            counter[entity_name] += len(keywords)
    return counter


_KOREA_SIDO_GEOJSON_URL = (
    "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/"
    "kostat/2013/json/skorea_provinces_geo.json"
)

_SIDO_ALIASES = {
    "서울": "서울특별시",
    "서울시": "서울특별시",
    "서울특별시": "서울특별시",
    "seoul": "서울특별시",
    "부산": "부산광역시",
    "부산시": "부산광역시",
    "부산광역시": "부산광역시",
    "busan": "부산광역시",
    "대구": "대구광역시",
    "대구시": "대구광역시",
    "대구광역시": "대구광역시",
    "daegu": "대구광역시",
    "인천": "인천광역시",
    "인천시": "인천광역시",
    "인천광역시": "인천광역시",
    "incheon": "인천광역시",
    "광주": "광주광역시",
    "광주시": "광주광역시",
    "광주광역시": "광주광역시",
    "gwangju": "광주광역시",
    "대전": "대전광역시",
    "대전시": "대전광역시",
    "대전광역시": "대전광역시",
    "daejeon": "대전광역시",
    "울산": "울산광역시",
    "울산시": "울산광역시",
    "울산광역시": "울산광역시",
    "ulsan": "울산광역시",
    "세종": "세종특별자치시",
    "세종시": "세종특별자치시",
    "세종특별자치시": "세종특별자치시",
    "sejong": "세종특별자치시",
    "경기": "경기도",
    "경기도": "경기도",
    "gyeonggi": "경기도",
    "강원": "강원도",
    "강원도": "강원도",
    "강원특별자치도": "강원도",
    "gangwon": "강원도",
    "충북": "충청북도",
    "충청북도": "충청북도",
    "chungcheongbuk": "충청북도",
    "충남": "충청남도",
    "충청남도": "충청남도",
    "chungcheongnam": "충청남도",
    "전북": "전라북도",
    "전라북도": "전라북도",
    "전북특별자치도": "전라북도",
    "jeollabuk": "전라북도",
    "전남": "전라남도",
    "전라남도": "전라남도",
    "jeollanam": "전라남도",
    "경북": "경상북도",
    "경상북도": "경상북도",
    "gyeongsangbuk": "경상북도",
    "경남": "경상남도",
    "경상남도": "경상남도",
    "gyeongsangnam": "경상남도",
    "제주": "제주특별자치도",
    "제주시": "제주특별자치도",
    "제주도": "제주특별자치도",
    "제주특별자치도": "제주특별자치도",
    "jeju": "제주특별자치도",
}

_NORMALIZED_SIDO_ALIASES = {
    re.sub(r"\s+", "", alias).lower(): canonical for alias, canonical in _SIDO_ALIASES.items()
}

_SORTED_SIDO_ALIASES = sorted(
    _NORMALIZED_SIDO_ALIASES.items(), key=lambda item: len(item[0]), reverse=True
)


def _extract_sido_name(text: str) -> str | None:
    normalized = re.sub(r"\s+", "", text).lower().strip()
    if not normalized:
        return None

    direct = _NORMALIZED_SIDO_ALIASES.get(normalized)
    if direct:
        return direct

    for alias, canonical in _SORTED_SIDO_ALIASES:
        if alias in normalized:
            return canonical
    return None


def _count_sido_mentions(entities_json_rows: Iterable[str]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for raw_entities in entities_json_rows:
        if not raw_entities:
            continue
        try:
            parsed = json.loads(raw_entities)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue

        matched_in_article: set[str] = set()
        parsed_dict = cast(dict[object, object], parsed)
        for entity_name, keywords in parsed_dict.items():
            if isinstance(entity_name, str):
                extracted_entity = _extract_sido_name(entity_name)
                if extracted_entity:
                    matched_in_article.add(extracted_entity)
            if not isinstance(keywords, list):
                continue
            for keyword in keywords:
                if not isinstance(keyword, str):
                    continue
                extracted_keyword = _extract_sido_name(keyword)
                if extracted_keyword:
                    matched_in_article.add(extracted_keyword)

        for region_name in matched_in_article:
            counts[region_name] += 1
    return counts


def _build_korea_choropleth_map_html(region_counts: Counter[str]) -> str | None:
    if not region_counts:
        return None

    try:
        import plotly.express as px
    except ImportError:
        return None

    regional_rows = sorted(region_counts.items(), key=lambda item: (-item[1], item[0]))
    locations = [name for name, _count in regional_rows]
    values = [count for _name, count in regional_rows]

    try:
        fig = px.choropleth_mapbox(
            {
                "region": locations,
                "availability": values,
            },
            geojson=_KOREA_SIDO_GEOJSON_URL,
            locations="region",
            color="availability",
            featureidkey="properties.name",
            color_continuous_scale="Tealgrn",
            mapbox_style="carto-positron",
            center={"lat": 36.35, "lon": 127.8},
            zoom=6,
            opacity=0.72,
            labels={"availability": "Mentions"},
        )
    except Exception:
        return None

    fig.update_traces(
        marker_line_color="rgba(255, 255, 255, 0.55)",
        marker_line_width=0.8,
        hovertemplate="%{location}<br>Mentions: %{z}<extra></extra>",
    )
    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar={"title": "Mentions", "thickness": 16},
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn", default_height=420)


def generate_index_html(report_dir: Path) -> Path:
    """Generate an index.html that lists all available report files."""
    report_dir.mkdir(parents=True, exist_ok=True)

    html_files = sorted(
        [f for f in report_dir.glob("*.html") if f.name != "index.html"],
        key=lambda p: p.name,
    )

    reports = []
    for html_file in html_files:
        name = html_file.stem
        display_name = name.replace("_report", "").replace("_", " ").title()
        reports.append({"filename": html_file.name, "display_name": display_name})

    template = _get_jinja_env().get_template("index.html")
    rendered = template.render(
        reports=reports,
        generated_at=datetime.now(UTC),
    )

    index_path = report_dir / "index.html"
    _ = index_path.write_text(rendered, encoding="utf-8")
    return index_path
