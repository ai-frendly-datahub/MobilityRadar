from __future__ import annotations

from dataclasses import dataclass, field

# Re-export from radar-core shared package
from radar_core.models import (
    Article,
    CategoryConfig,
    EmailSettings,
    EntityDefinition,
    NotificationConfig,
    RadarSettings,
    TelegramSettings,
)


__all__ = [
    "Article",
    "CategoryConfig",
    "EmailSettings",
    "EntityDefinition",
    "NotificationConfig",
    "RadarSettings",
    "Source",
    "TelegramSettings",
]


# MobilityRadar-specific: Source with extra options field
@dataclass
class Source:
    name: str
    type: str
    url: str
    options: dict[str, object] = field(default_factory=dict)
