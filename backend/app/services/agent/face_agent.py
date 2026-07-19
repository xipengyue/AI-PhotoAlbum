"""Face Agent --- InsightFace-powered face recognition specialist agent.

Responsibilities:
  - Search photos by person name via face-identity matching
  - List unnamed face clusters that need naming
  - Provide face-cluster statistics
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from langchain_core.tools import tool

from app.services.search_service import (
    search_faces_by_name,
    get_unnamed_candidates,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Face agent tools
# ---------------------------------------------------------------------------

@tool
def search_faces(
    person_name: str,
) -> dict:
    """Search for photos containing a named person via face identity matching.

    Call when the user asks about a specific person, e.g. "find photos of mom" or "photos with Xiao Ming".

    Args:
        person_name: The person''s name as stored in the face identity system, e.g. "mom", "dad", "Xiao Ming".
                     Supports Chinese kinship terms and given names.
    """
    pass  # implemented in run_face_agent


@tool
def list_unnamed_faces() -> dict:
    """List unnamed face clusters that the user has not yet identified.

    Call when the user asks "who are the people I haven''t named" or "show me unknown faces".
    Returns the top candidates for name confirmation.
    """
    pass


# ---------------------------------------------------------------------------
# Face agent runner
# ---------------------------------------------------------------------------

def run_face_agent(
    person_name: Optional[str] = None,
    action: str = "search",
    db: Optional[Session] = None,
    owner_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Entry point for the Face Agent.

    Args:
        person_name: Name to search for (when action="search").
        action: "search" | "unnamed_list"
        db: Database session.
        owner_id: Current user UUID.

    Returns:
        For search: {"found": int, "photo_ids": [str]}
        For unnamed_list: {"clusters": [{"cluster_id": str, "face_count": int, ...}]}
    """
    if not db or not owner_id:
        return {"error": "db session and owner_id required"}

    if action == "search":
        if not person_name:
            return {"found": 0, "photo_ids": [],
                    "message": "no person name provided"}

        photo_ids = search_faces_by_name(db, person_name, owner_id)
        if photo_ids:
            return {
                "found": len(photo_ids),
                "photo_ids": photo_ids,
                "person_name": person_name,
            }
        else:
            # No exact match --- suggest candidates
            candidates = get_unnamed_candidates(db, owner_id, top_k=5)
            return {
                "found": 0,
                "photo_ids": [],
                "person_name": person_name,
                "needs_confirmation": True,
                "pending_candidates": [
                    {
                        "cluster_id": c.get("cluster_id"),
                        "face_count": c.get("face_count", 0),
                    }
                    for c in (candidates or [])
                ],
            }

    elif action == "unnamed_list":
        candidates = get_unnamed_candidates(db, owner_id, top_k=10)
        return {
            "clusters": [
                {
                    "cluster_id": c.get("cluster_id"),
                    "face_count": c.get("face_count", 0),
                }
                for c in (candidates or [])
            ],
            "total_unnamed": len(candidates) if candidates else 0,
        }

    return {"error": f"unknown action: {action}"}


__all__ = [
    "search_faces",
    "list_unnamed_faces",
    "run_face_agent",
]