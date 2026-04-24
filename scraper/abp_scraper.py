"""
ABP-CVoter and News18 poll scraper.
These agencies publish structured poll data; fallback to mock on failure.
"""
import re
import logging
from datetime import date, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from scraper.base_scraper import BaseScraper, normalize_party

logger = logging.getLogger("tn2026.scraper.abp")

MOCK_ABP_DATA = [
    {"source": "ABP-CVoter", "date": "2025-07-20", "party": "DMK",    "vote_share": 44.9, "seat_low": 132, "seat_high": 152, "region": "statewide"},
    {"source": "ABP-CVoter", "date": "2025-07-20", "party": "AIADMK", "vote_share": 28.4, "seat_low": 58,  "seat_high": 76,  "region": "statewide"},
    {"source": "ABP-CVoter", "date": "2025-07-20", "party": "BJP",    "vote_share": 12.9, "seat_low": 9,   "seat_high": 19,  "region": "statewide"},
    {"source": "ABP-CVoter", "date": "2025-07-20", "party": "PMK",    "vote_share": 5.6,  "seat_low": 8,   "seat_high": 14,  "region": "statewide"},
    {"source": "ABP-CVoter", "date": "2025-10-05", "party": "DMK",    "vote_share": 45.5, "seat_low": 134, "seat_high": 154, "region": "statewide"},
    {"source": "ABP-CVoter", "date": "2025-10-05", "party": "AIADMK", "vote_share": 27.8, "seat_low": 55,  "seat_high": 73,  "region": "statewide"},
    {"source": "ABP-CVoter", "date": "2025-10-05", "party": "BJP",    "vote_share": 13.3, "seat_low": 10,  "seat_high": 20,  "region": "statewide"},
    # Regional breakdowns
    {"source": "ABP-CVoter", "date": "2025-10-05", "party": "DMK",    "vote_share": 48.2, "seat_low": 35, "seat_high": 42, "region": "Chennai"},
    {"source": "ABP-CVoter", "date": "2025-10-05", "party": "AIADMK", "vote_share": 24.5, "seat_low": 15, "seat_high": 20, "region": "Chennai"},
    {"source": "ABP-CVoter", "date": "2025-10-05", "party": "DMK",    "vote_share": 40.1, "seat_low": 28, "seat_high": 35, "region": "Western TN"},
    {"source": "ABP-CVoter", "date": "2025-10-05", "party": "AIADMK", "vote_share": 32.3, "seat_low": 18, "seat_high": 25, "region": "Western TN"},
]

MOCK_NEWS18_DATA = [
    {"source": "News18", "date": "2025-08-12", "party": "DMK",    "vote_share": 45.0, "seat_low": 133, "seat_high": 151, "region": "statewide"},
    {"source": "News18", "date": "2025-08-12", "party": "AIADMK", "vote_share": 28.2, "seat_low": 57,  "seat_high": 75,  "region": "statewide"},
    {"source": "News18", "date": "2025-08-12", "party": "BJP",    "vote_share": 13.0, "seat_low": 9,   "seat_high": 19,  "region": "statewide"},
    {"source": "News18", "date": "2025-11-20", "party": "DMK",    "vote_share": 46.0, "seat_low": 136, "seat_high": 156, "region": "statewide"},
    {"source": "News18", "date": "2025-11-20", "party": "AIADMK", "vote_share": 27.0, "seat_low": 52,  "seat_high": 70,  "region": "statewide"},
    {"source": "News18", "date": "2025-11-20", "party": "BJP",    "vote_share": 13.8, "seat_low": 11,  "seat_high": 21,  "region": "statewide"},
]


class ABPCVoterScraper(BaseScraper):
    name = "ABP-CVoter"
    base_url = "https://news.abplive.com/elections/tamil-nadu"
    delay_range = (2.0, 4.0)

    async def scrape(self) -> List[Dict]:
        logger.info("ABP-CVoter: Starting scrape...")
        html = await self.fetch(f"{self.base_url}/opinion-poll")

        if html:
            records = self._parse_html(html)
            if records:
                logger.info(f"ABP-CVoter: {len(records)} live records")
                return records

        logger.warning("ABP-CVoter: Using mock data")
        return MOCK_ABP_DATA

    def _parse_html(self, html: str) -> List[Dict]:
        records = []
        soup = BeautifulSoup(html, "lxml")

        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) >= 2:
                    try:
                        party = normalize_party(cells[0])
                        if not party:
                            continue
                        vote_str = re.sub(r"[^0-9.]", "", cells[1])
                        if not vote_str:
                            continue
                        vote_share = float(vote_str)
                        seat_match = re.findall(r"\d+", cells[2]) if len(cells) > 2 else []
                        seat_low = int(seat_match[0]) if seat_match else 0
                        seat_high = int(seat_match[1]) if len(seat_match) > 1 else seat_low + 10

                        records.append({
                            "source": "ABP-CVoter",
                            "date": date.today().isoformat(),
                            "party": party,
                            "vote_share": vote_share,
                            "seat_low": seat_low,
                            "seat_high": seat_high,
                            "region": "statewide",
                            "raw": {"cells": cells},
                        })
                    except Exception:
                        continue
        return records


class News18Scraper(BaseScraper):
    name = "News18"
    base_url = "https://www.news18.com/elections/tamil-nadu"
    delay_range = (1.5, 3.5)

    async def scrape(self) -> List[Dict]:
        logger.info("News18: Starting scrape...")
        html = await self.fetch(f"{self.base_url}/poll-of-polls")

        if html:
            records = self._parse_html(html)
            if records:
                logger.info(f"News18: {len(records)} live records")
                return records

        logger.warning("News18: Using mock data")
        return MOCK_NEWS18_DATA

    def _parse_html(self, html: str) -> List[Dict]:
        # Similar to ABP parser — News18 uses comparable table structure
        records = []
        soup = BeautifulSoup(html, "lxml")
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all(["td"])]
                if len(cells) >= 2:
                    try:
                        party = normalize_party(cells[0])
                        if not party:
                            continue
                        vote_str = re.sub(r"[^0-9.]", "", cells[1])
                        if not vote_str:
                            continue
                        vote_share = float(vote_str)
                        seat_match = re.findall(r"\d+", cells[2]) if len(cells) > 2 else []
                        seat_low = int(seat_match[0]) if seat_match else 0
                        seat_high = int(seat_match[1]) if len(seat_match) > 1 else seat_low + 10
                        records.append({
                            "source": "News18",
                            "date": date.today().isoformat(),
                            "party": party,
                            "vote_share": vote_share,
                            "seat_low": seat_low,
                            "seat_high": seat_high,
                            "region": "statewide",
                            "raw": {"cells": cells},
                        })
                    except Exception:
                        continue
        return records
