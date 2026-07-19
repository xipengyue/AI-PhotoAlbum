"""Metadata Agent --- EXIF/time/location specialist agent.

Responsibilities:
  - Search photos by time range (natural language -> datetime)
  - Search photos by location (natural language -> GPS/address keywords)
  - Search photos by city name via GPS bounding box (fallback for non-geocoded EXIF)
  - Search photos by camera model / device
  - Combine time + location + camera filters in a single query
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy import and_
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
# Chinese city GPS lookup  (approximate center coordinates, ±offset for bounds)
# ---------------------------------------------------------------------------
# Used as fallback when reverse geocoding is not available in the EXIF pipeline.
# The offsets (~0.75°) give roughly a 50-80 km bounding box around each city.

_CITY_GPS_MAP: dict = {
    # 直辖市
    "北京": (39.9042, 116.4074, 0.6),
    "上海": (31.2304, 121.4737, 0.5),
    "天津": (39.1252, 117.1908, 0.5),
    "重庆": (29.4316, 106.9123, 0.8),
    # 省会城市
    "广州": (23.1291, 113.2644, 0.5),
    "深圳": (22.5431, 114.0579, 0.4),
    "成都": (30.5728, 104.0668, 0.5),
    "武汉": (30.5928, 114.3055, 0.5),
    "杭州": (30.2741, 120.1551, 0.4),
    "南京": (32.0603, 118.7969, 0.4),
    "西安": (34.3416, 108.9398, 0.5),
    "长沙": (28.2282, 112.9388, 0.5),
    "青岛": (36.0671, 120.3826, 0.4),
    "大连": (38.9140, 121.6147, 0.4),
    "厦门": (24.4798, 118.0894, 0.4),
    "苏州": (31.2990, 120.5853, 0.4),
    "宁波": (29.8683, 121.5440, 0.4),
    "济南": (36.6512, 117.1201, 0.4),
    "郑州": (34.7466, 113.6254, 0.4),
    "沈阳": (41.8057, 123.4315, 0.4),
    "昆明": (25.0389, 102.7183, 0.5),
    "哈尔滨": (45.8038, 126.5350, 0.5),
    "合肥": (31.8206, 117.2272, 0.4),
    "福州": (26.0743, 119.2965, 0.4),
    "南宁": (22.8170, 108.3665, 0.4),
    "贵阳": (26.6470, 106.6302, 0.4),
    "海口": (20.0440, 110.3498, 0.4),
    "兰州": (36.0611, 103.8343, 0.4),
    "银川": (38.4872, 106.2309, 0.4),
    "西宁": (36.6171, 101.7782, 0.4),
    "拉萨": (29.6500, 91.1000, 0.5),
    "乌鲁木齐": (43.8256, 87.6168, 0.5),
    "呼和浩特": (40.8422, 111.7498, 0.4),
    "石家庄": (38.0428, 114.5149, 0.4),
    "南昌": (28.6829, 115.8582, 0.4),
    "太原": (37.8706, 112.5489, 0.4),
    "三亚": (18.2528, 109.5120, 0.4),
    "珠海": (22.2710, 113.5668, 0.3),
}


def _filter_photos_by_gps_bounds(
    db: Session,
    owner_id: str,
    location_name: str,
) -> List[str]:
    """Search photos by GPS bounding box for known Chinese cities.

    Handles city names with or without the "市" suffix.
    Returns photo_id strings.
    """
    # Try direct match first, then with "市" suffix, then without
    candidate = None
    if location_name in _CITY_GPS_MAP:
        candidate = _CITY_GPS_MAP[location_name]
    elif location_name.endswith("市") and location_name[:-1] in _CITY_GPS_MAP:
        candidate = _CITY_GPS_MAP[location_name[:-1]]
    elif f"{location_name}市" in _CITY_GPS_MAP:
        candidate = _CITY_GPS_MAP[f"{location_name}市"]

    if candidate is None:
        return []

    lat, lng, offset = candidate
    min_lat, max_lat = lat - offset, lat + offset
    min_lng, max_lng = lng - offset, lng + offset

    owner_uuid = UUID(owner_id)
    rows = (
        db.query(PhotoMetadata.photo_id)
        .join(Photo, Photo.id == PhotoMetadata.photo_id)
        .filter(
            Photo.owner_id == owner_uuid,
            Photo.is_deleted == False,
            PhotoMetadata.latitude.isnot(None),
            PhotoMetadata.longitude.isnot(None),
            and_(
                PhotoMetadata.latitude.between(min_lat, max_lat),
                PhotoMetadata.longitude.between(min_lng, max_lng),
            ),
        )
        .distinct()
        .all()
    )
    return [str(r[0]) for r in rows]


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

    Search strategy (3-tier, in order):
      1. Text-based location filter (queries city/province/address fields)
      2. GPS bounding-box filter (uses CITY_GPS_MAP for lat/lng range query)
      3. GPS fallback when text fields are NULL (no reverse geocoding during upload)

    Returns:
        {"found": int, "photo_ids": [str], "filters_applied": {...}}
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

    # Location filter  (3-tier: text -> GPS bounding box)
    if location:
        # Tier 1: text-based search (city/province/address fields)
        keywords = extract_location_keywords(location, [location])
        if not keywords:
            keywords = [location]
        loc_ids = filter_photos_by_location(db, owner_id, keywords)

        # Tier 2: if text search returned nothing, try GPS bounding box
        if not loc_ids:
            gps_ids = _filter_photos_by_gps_bounds(db, owner_id, location)
            if gps_ids:
                logger.info(f"Location search fallback: GPS bounding box matched {len(gps_ids)} photos for '{location}'")
                loc_ids = gps_ids

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
    "CITY_GPS_MAP",
]