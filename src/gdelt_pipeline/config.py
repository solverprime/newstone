"""Configuration values for the GDELT tone analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

ANALYSIS_WINDOW = (datetime(2015, 10, 16), datetime(2025, 10, 15, 23, 59, 59))


@dataclass(frozen=True)
class PlaceSpec:
    """Definition of a place in the analysis."""

    name: str
    slug: str
    domains: List[str]


PLACE_SPECS: Dict[str, PlaceSpec] = {
    "switzerland": PlaceSpec(
        name="Switzerland",
        slug="switzerland",
        domains=[
            "swissinfo.ch",
            "swissinfo.org",
            "thelocal.ch",
            "blick.ch",
            "nzz.ch",
            "rts.ch",
        ],
    ),
    "singapore": PlaceSpec(
        name="Singapore",
        slug="singapore",
        domains=[
            "straitstimes.com",
            "channelnewsasia.com",
            "todayonline.com",
            "businesstimes.com.sg",
            "mothership.sg",
        ],
    ),
    "new_york": PlaceSpec(
        name="New York",
        slug="new_york",
        domains=[
            "nytimes.com",
            "nypost.com",
            "nydailynews.com",
            "amny.com",
            "gothamist.com",
        ],
    ),
    "denver": PlaceSpec(
        name="Denver",
        slug="denver",
        domains=[
            "denverpost.com",
            "9news.com",
            "westword.com",
            "denverite.com",
            "coloradosun.com",
        ],
    ),
    "hyderabad": PlaceSpec(
        name="Hyderabad",
        slug="hyderabad",
        domains=[
            "telanganatoday.com",
            "deccanchronicle.com",
            "timesofindia.indiatimes.com",
            "thehindu.com",
            "eenadu.net",
        ],
    ),
}

ALL_DOMAINS = sorted({domain for spec in PLACE_SPECS.values() for domain in spec.domains})
