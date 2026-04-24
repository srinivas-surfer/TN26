"""
Base scraper: shared async HTTP session, retry logic, rate limiting.
All scrapers inherit from this.
"""
import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import httpx

logger = logging.getLogger("tn2026.scraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Normalized poll record schema
POLL_SCHEMA = {
    "source": str,
    "date": str,         # ISO format: YYYY-MM-DD
    "party": str,
    "vote_share": float,
    "seat_low": int,
    "seat_high": int,
    "region": str,       # "statewide" or specific region
    "raw": dict,         # original scraped data
}


class BaseScraper(ABC):
    name: str = "base"
    base_url: str = ""
    delay_range: tuple = (1.0, 3.0)

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            headers=HEADERS,
            timeout=15.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=2),
        )
        return self

    async def __aexit__(self, *args):
        if self.client:
            await self.client.aclose()

    async def fetch(self, url: str, retries: int = 3) -> Optional[str]:
        """Fetch URL with retry and polite delay."""
        for attempt in range(retries):
            try:
                await asyncio.sleep(random.uniform(*self.delay_range))
                resp = await self.client.get(url)
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = 10 * (attempt + 1)
                    logger.warning(f"{self.name}: rate-limited, waiting {wait}s")
                    await asyncio.sleep(wait)
                elif e.response.status_code in (403, 404):
                    logger.warning(f"{self.name}: {e.response.status_code} for {url}")
                    return None
                else:
                    logger.error(f"{self.name}: HTTP {e.response.status_code}")
            except Exception as e:
                logger.warning(f"{self.name}: attempt {attempt+1} failed: {e}")
                await asyncio.sleep(2 ** attempt)
        return None

    @abstractmethod
    async def scrape(self) -> List[Dict]:
        """Return list of normalized poll records."""
        ...

    def validate_record(self, record: dict) -> bool:
        """Check required fields exist and types are correct."""
        required = ["source", "date", "party", "vote_share", "region"]
        for field in required:
            if field not in record:
                return False
        if not (0 < record["vote_share"] < 100):
            return False
        return True
