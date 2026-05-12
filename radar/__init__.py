from __future__ import annotations

import sys
from importlib import import_module


_MODULE_ALIASES = {
    "analyzer": "mobilityradar.analyzer",
    "collector": "mobilityradar.collector",
    "exceptions": "mobilityradar.exceptions",
    "models": "mobilityradar.models",
    "nl_query": "mobilityradar.nl_query",
    "search_index": "mobilityradar.search_index",
    "storage": "mobilityradar.storage",
}

for _module_name, _target in _MODULE_ALIASES.items():
    sys.modules[f"{__name__}.{_module_name}"] = import_module(_target)


RadarStorage = import_module("mobilityradar.storage").RadarStorage


__all__ = ["RadarStorage"]
