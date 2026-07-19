"""Agent service submodule --- search agents, specialists, supervisor, and chat management."""

from app.services.agent.search_agent import run_search_agent, SearchState
from app.services.agent.chat_agent import (
    create_session, list_sessions, get_session, get_messages, send_message,
)
from app.services.agent.detection_agent import run_detection_agent
from app.services.agent.face_agent import run_face_agent
from app.services.agent.metadata_agent import run_metadata_agent
from app.services.agent.supervisor import run_supervisor

__all__ = [
    # Search
    "run_search_agent", "SearchState",
    # Chat
    "create_session", "list_sessions", "get_session", "get_messages", "send_message",
    # Specialists
    "run_detection_agent",
    "run_face_agent",
    "run_metadata_agent",
    # Supervisor
    "run_supervisor",
]