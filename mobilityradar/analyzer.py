from __future__ import annotations

import re
from typing import Iterable, List

from .models import Article, EntityDefinition


def apply_entity_rules(articles: Iterable[Article], entities: List[EntityDefinition]) -> List[Article]:
    """Attach matched entity keywords to each article via simple keyword search."""
    analyzed: List[Article] = []
    normalized_entities = [_normalize_entity_keywords(entity) for entity in entities]

    for article in articles:
        haystack = f"{article.title}\n{article.summary}".casefold()
        normalized_haystack = _normalize_text(haystack)
        matches: dict[str, list[str]] = {}
        for entity, normalized_keywords in zip(entities, normalized_entities, strict=False):
            hit_keywords: list[str] = []
            for keyword in normalized_keywords:
                if keyword.raw in haystack or keyword.normalized in normalized_haystack:
                    hit_keywords.append(keyword.raw)
            if hit_keywords:
                matches[entity.name] = hit_keywords
        article.matched_entities = matches
        analyzed.append(article)

    return analyzed


class _NormalizedKeyword:
    def __init__(self, raw: str, normalized: str) -> None:
        self.raw = raw
        self.normalized = normalized


def _normalize_entity_keywords(entity: EntityDefinition) -> list[_NormalizedKeyword]:
    keywords: list[_NormalizedKeyword] = []
    for keyword in entity.keywords:
        raw = keyword.casefold().strip()
        if not raw:
            continue
        keywords.append(_NormalizedKeyword(raw=raw, normalized=_normalize_text(raw)))
    return keywords


def _normalize_text(value: str) -> str:
    normalized = re.sub(r"[-_/]", " ", value)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()
