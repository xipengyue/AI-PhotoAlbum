"""Metadata Agent --- EXIF/time/location specialist agent.

Responsibilities:
  - Search photos by time range (natural language -> datetime)
  - Search photos by location (natural language -> GPS/address keywords)
  - Search photos by camera model / device
  - Combine time + location + camera filters in a single query
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from langchain_core.tools import tool

from app.services.search_service import (
    extract_time_range,
    extract_location_keywords,
    filter_photos_by_time,
    filter_photos_by_location,
)
from app.models.photo import Photo, PhotoMetadata

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Metadata agent tool
# ---------------------------------------------------------------------------

@tool
def search_by_metadata(
    time_range: Optional[str] = None,
    location: Optional[str] = None,
    camera_model: Optional[str] = None,
) -> dict:
    """Search photos by metadata: time period, location, and/or camera model.

    Call when the user asks about photos taken at a specific time, place, or with a specific device.
    Examples: "photos from last summer", "photos taken in Shanghai", "iPhone photos from 2024".

    Args:
        time_range: Natural-language time expression, e.g. "last summer", "2024 March", "two years ago".
                    Leave empty if no time filter.
        location: Location name, e.g. "Shanghai", "Beijing", "West Lake".
                  Leave empty if no location filter.
        camera_model: Camera or phone model, e.g. "iPhone 15", "Canon EOS", "Huawei".
                      Leave empty if no device filter.
    """
    pass  # implemented in run_metadata_agent


# ---------------------------------------------------------------------------
# Metadata agent runner
# ---------------------------------------------------------------------------

def _parse_time_range(
    query: str,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse natural-language time expression into datetime range."""
    if not query:
        return None, None
    try:
        start, end = extract_time_range(query, datetime.now())
        return start, end
    except Exception as e:
        logger.warning(f"Failed to parse time range '{query}': {e}")
        return None, None


def run_metadata_agent(
    time_range: Optional[str] = None,
    location: Optional[str] = None,
    camera_model: Optional[str] = None,
    db: Optional[Session] = None,
    owner_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Entry point for the Metadata Agent.

    Returns:
        {"found": int, "photo_ids": [str], "filters_applied": {time: str|None, location: str|None, camera: str|None}}
    """
    if not db or not owner_id:
        return {"error": "db session and owner_id required"}

    owner_uuid = UUID(owner_id)
    filters_applied = {
        "time": time_range,
        "location": location,
        "camera": camera_model,
    }

    # --- Collect candidate photo IDs from each filter ---

    time_ids: Optional[List[str]] = None
    loc_ids: Optional[List[str]] = None
    camera_ids: Optional[List[str]] = None

    # Time filter
    if time_range:
        start, end = _parse_time_range(time_range)
        if start or end:
            time_ids = filter_photos_by_time(db, owner_id, start=start, end=end)

    # Location filter
    if location:
        # Extract location keywords from the natural-language location string
        keywords = extract_location_keywords(location, [location]) if location else [location]
        loc_ids = filter_photos_by_location(db, owner_id, keywords)

    # Camera filter
    if camera_model:
        pattern = f"%{camera_model}%"
        rows = (
            db.query(PhotoMetadata.photo_id)
            .join(Photo, Photo.id == PhotoMetadata.photo_id)
            .filter(
                Photo.owner_id == owner_uuid,
                Photo.is_deleted == False,
                PhotoMetadata.camera_model.ilike(pattern),
            )
            .distinct()
            .all()
        )
        camera_ids = [str(r[0]) for r in rows]

    # --- Intersect results ---
    candidate_sets = [s for s in [time_ids, loc_ids, camera_ids] if s is not None and len(s) > 0]

    if not candidate_sets:
        return {"found": 0, "photo_ids": [], "filters_applied": filters_applied,
                "message": "no filters applied or no results"}

    # Intersection
    common = set(candidate_sets[0])
    for s in candidate_sets[1:]:
        common &= set(s)

    photo_ids = list(common)

    return {
        "found": len(photo_ids),
        "photo_ids": photo_ids,
        "filters_applied": filters_applied,
    }


__all__ = [
    "search_by_metadata",
    "run_metadata_agent",
]