"""
Normalizer: cleans, validates, deduplicates poll records from all scrapers.
Produces a consistent schema for MongoDB storage.
"""
import hashlib
import logging
from datetime import datetime, date
from typing import List, Dict, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger("tn2026.normalizer")

VALID_PARTIES = {"DMK", "AIADMK", "BJP", "Congress", "PMK", "VCK", "NTK", "ADMK"}
VALID_REGIONS = {"statewide", "Chennai", "Western TN", "Southern TN", "Central TN", "Northern TN", "Delta TN"}


def record_hash(record: dict) -> str:
    """Deterministic hash for deduplication."""
    key = f"{record['source']}:{record['date']}:{record['party']}:{record['region']}"
    return hashlib.md5(key.encode()).hexdigest()


def clean_vote_share(val) -> Optional[float]:
    """Parse and validate vote share value."""
    try:
        v = float(str(val).replace("%", "").strip())
        if 0 < v < 100:
            return round(v, 2)
    except (ValueError, TypeError):
        pass
    return None


def clean_date(val) -> Optional[str]:
    """Normalize date to ISO format string."""
    if isinstance(val, (date, datetime)):
        return val.date().isoformat() if isinstance(val, datetime) else val.isoformat()
    try:
        from dateutil.parser import parse
        return parse(str(val)).date().isoformat()
    except Exception:
        return None


def normalize_records(raw_records: List[Dict]) -> List[Dict]:
    """
    Clean, validate, and deduplicate a list of poll records.
    Returns list ready for MongoDB insertion.
    """
    cleaned = []
    seen_hashes = set()

    for rec in raw_records:
        try:
            party = str(rec.get("party", "")).strip()
            if party not in VALID_PARTIES:
                logger.debug(f"Skipping unknown party: {party}")
                continue

            vote_share = clean_vote_share(rec.get("vote_share"))
            if vote_share is None:
                logger.debug(f"Invalid vote_share: {rec.get('vote_share')}")
                continue

            clean_rec_date = clean_date(rec.get("date"))
            if not clean_rec_date:
                logger.debug(f"Invalid date: {rec.get('date')}")
                continue

            region = str(rec.get("region", "statewide")).strip()
            if region not in VALID_REGIONS:
                region = "statewide"

            source = str(rec.get("source", "unknown")).strip()

            # Seat range
            seat_low = int(rec.get("seat_low", 0))
            seat_high = int(rec.get("seat_high", seat_low + 10))
            if seat_low > seat_high:
                seat_low, seat_high = seat_high, seat_low
            seat_mid = (seat_low + seat_high) / 2

            normalized = {
                "source": source,
                "date": clean_rec_date,
                "party": party,
                "vote_share": vote_share,
                "seat_low": max(0, seat_low),
                "seat_high": min(234, seat_high),
                "seat_mid": seat_mid,
                "region": region,
                "created_at": datetime.utcnow().isoformat(),
            }

            h = record_hash(normalized)
            if h not in seen_hashes:
                seen_hashes.add(h)
                normalized["_hash"] = h
                cleaned.append(normalized)

        except Exception as e:
            logger.warning(f"Record normalization error: {e} — {rec}")

    logger.info(f"Normalized {len(cleaned)}/{len(raw_records)} records")
    return cleaned


def aggregate_poll_of_polls(records: List[Dict]) -> List[Dict]:
    """
    Compute weighted average across all sources for the same party+date.
    Weight newer polls higher.
    """
    if not records:
        return []

    df = pd.DataFrame(records)
    df["date_dt"] = pd.to_datetime(df["date"])
    df = df[df["region"] == "statewide"]

    if df.empty:
        return []

    # Weight: newer = higher weight
    max_date = df["date_dt"].max()
    df["days_ago"] = (max_date - df["date_dt"]).dt.days
    df["weight"] = np.exp(-df["days_ago"] / 90)  # exponential decay, 90-day half-life

    aggregated = []
    for party, group in df.groupby("party"):
        w = group["weight"].values
        w_sum = w.sum()
        if w_sum == 0:
            continue
        agg = {
            "party": party,
            "vote_share_wavg": round(float(np.average(group["vote_share"], weights=w)), 2),
            "seat_low_wavg": int(round(np.average(group["seat_low"], weights=w))),
            "seat_high_wavg": int(round(np.average(group["seat_high"], weights=w))),
            "source_count": int(group["source"].nunique()),
            "latest_date": group["date"].max(),
            "poll_count": len(group),
        }
        aggregated.append(agg)

    return aggregated
