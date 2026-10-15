"""Data model and extraction-level definitions."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List

# Fields available at each extraction level (levels are cumulative).
LEVEL1_FIELDS = ["name", "website", "emails", "phones"]
LEVEL2_FIELDS = ["social_profiles", "address", "tagline", "description",
                 "founded", "industry", "products_services"]
LEVEL3_FIELDS = ["tech_stack", "current_projects", "competitors",
                 "market_positioning"]
META_FIELDS = ["pages_scraped", "warnings"]


def fields_for_level(level: int) -> List[str]:
    fields = list(LEVEL1_FIELDS)
    if level >= 2:
        fields += LEVEL2_FIELDS
    if level >= 3:
        fields += LEVEL3_FIELDS
    return fields + META_FIELDS


@dataclass
class Company:
    # Level 1
    name: str = ""
    website: str = ""
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    # Level 2
    social_profiles: Dict[str, str] = field(default_factory=dict)
    address: str = ""
    tagline: str = ""
    description: str = ""
    founded: str = ""
    industry: str = ""
    products_services: List[str] = field(default_factory=list)
    # Level 3
    tech_stack: List[str] = field(default_factory=list)
    current_projects: List[str] = field(default_factory=list)
    competitors: List[str] = field(default_factory=list)
    market_positioning: str = ""
    # Meta
    pages_scraped: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self, level: int = 3) -> dict:
        data = asdict(self)
        return {k: data[k] for k in fields_for_level(level)}
