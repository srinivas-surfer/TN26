"""
NDTV Election scraper.
Targets NDTV's election poll/survey pages for Tamil Nadu.
Falls back to mock data if live scraping fails (for development).
"""
import re
import json
import logging
from datetime import date
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from scraper.base_scraper import BaseScraper

logger = logging.getLogger("tn2026.scraper.ndtv")

PARTY_ALIASES = {
    "dmk": "DMK", "dravida munnetra kazhagam": "DMK",
    "aiadmk": "AIADMK", "all india anna dravida munnetra kazhagam": "AIADMK",
    "bjp": "BJP", "bharatiya janata party": "BJP",
    "inc": "Congress", "congress": "Congress", "indian national congress": "Congress",
    "pmk": "PMK", "pattali makkal katchi": "PMK",
    "vck": "VCK", "viduthalai chiruthaigal katchi": "VCK",
    "ntk": "NTK", "naam tamilar katchi": "NTK",
}


def normalize_party(raw: str) -> Optional[str]:
    key = raw.lower().strip()
    return PARTY_ALIASES.get(key)


MOCK_NDTV_DATA = [
    {"source": "NDTV-Poll", "date": "2025-06-15", "party": "DMK",    "vote_share": 45.2, "seat_low": 133, "seat_high": 153, "region": "statewide"},
    {"source": "NDTV-Poll", "date": "2025-06-15", "party": "AIADMK", "vote_share": 28.1, "seat_low": 56,  "seat_high": 74,  "region": "statewide"},
    {"source": "NDTV-Poll", "date": "2025-06-15", "party": "BJP",    "vote_share": 13.1, "seat_low": 9,   "seat_high": 19,  "region": "statewide"},
    {"source": "NDTV-Poll", "date": "2025-06-15", "party": "PMK",    "vote_share": 5.2,  "seat_low": 7,   "seat_high": 13,  "region": "statewide"},
    {"source": "NDTV-Poll", "date": "2025-09-10", "party": "DMK",    "vote_share": 45.8, "seat_low": 135, "seat_high": 155, "region": "statewide"},
    {"source": "NDTV-Poll", "date": "2025-09-10", "party": "AIADMK", "vote_share": 27.5, "seat_low": 53,  "seat_high": 71,  "region": "statewide"},
    {"source": "NDTV-Poll", "date": "2025-09-10", "party": "BJP",    "vote_share": 13.5, "seat_low": 10,  "seat_high": 20,  "region": "statewide"},
]


class NDTVScraper(BaseScraper):
    name = "NDTV"
    base_url = "https://www.ndtv.com/elections/assembly/tamil-nadu"
    poll_url = f"{base_url}/opinion-polls"

    async def scrape(self) -> List[Dict]:
        logger.info("NDTV: Starting scrape...")
        html = await self.fetch(self.poll_url)

        if html:
            records = self._parse_html(html)
            if records:
                logger.info(f"NDTV: Scraped {len(records)} live records")
                return records

        # Fallback to mock if site unreachable / layout changed
        logger.warning("NDTV: Using mock data (live scrape unavailable)")
        return MOCK_NDTV_DATA

    def _parse_html(self, html: str) -> List[Dict]:
        """
        Parse NDTV election poll tables.
        NDTV typically uses class="poll-table" or similar.
        Layout-specific parsing — update when site changes.
        """
        records = []
        soup = BeautifulSoup(html, "lxml")

        # Try JSON-LD first (structured data)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and "pollResults" in str(data):
                    # Extract if structured format available
                    pass
            except Exception:
                pass

        # Look for poll tables
        tables = soup.find_all("table", class_=re.compile(r"poll|survey|result", re.I))
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # skip header
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) >= 3:
                    record = self._parse_row(cells)
                    if record and self.validate_record(record):
                        records.append(record)

        return records

    def _parse_row(self, cells: list) -> Optional[Dict]:
        """Parse a table row into a poll record."""
        try:
            party_raw = cells[0]
            party = normalize_party(party_raw)
            if not party:
                return None

            vote_str = re.sub(r"[^0-9.]", "", cells[1])
            vote_share = float(vote_str) if vote_str else None
            if not vote_share:
                return None

            # Seat range: "130-150" or "140"
            seat_str = cells[2] if len(cells) > 2 else "0"
            seat_match = re.findall(r"\d+", seat_str)
            seat_low = int(seat_match[0]) if seat_match else 0
            seat_high = int(seat_match[1]) if len(seat_match) > 1 else seat_low + 10

            return {
                "source": "NDTV-Poll",
                "date": date.today().isoformat(),
                "party": party,
                "vote_share": vote_share,
                "seat_low": seat_low,
                "seat_high": seat_high,
                "region": "statewide",
                "raw": {"cells": cells},
            }
        except Exception as e:
            logger.debug(f"NDTV row parse error: {e}")
            return None
