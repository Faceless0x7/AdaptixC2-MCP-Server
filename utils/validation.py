"""
AdaptixC2 MCP — Validation Utilities
Input validation helpers for MCP tools.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from client.adaptix_client import AdaptixClient


class ValidationError(ValueError):
    """Raised when MCP tool input fails validation."""


def validate_agent_id(agent_id: str) -> str:
    """Ensure agent_id is a non-empty string."""
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise ValidationError("agent_id must be a non-empty string")
    return agent_id.strip()


def validate_port(port: int, name: str = "port") -> int:
    """Ensure port is in valid range 1-65535."""
    if not isinstance(port, int) or not (1 <= port <= 65535):
        raise ValidationError(f"{name} must be an integer between 1 and 65535, got: {port!r}")
    return port


def validate_nonempty(value: str, name: str) -> str:
    """Ensure a string field is non-empty."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")
    return value.strip()


async def validate_agent_exists(client: "AdaptixClient", agent_id: str) -> None:
    """
    Raises ValidationError if the agent is not found in the current agent list.
    Accepts both a_id (internal UUID) and a_crc (8-char hex shown in the GUI).
    """
    agents = await client.list_agents_raw()
    valid_ids = set()
    for a in agents:
        if a.get("a_id"):
            valid_ids.add(a["a_id"])
        if a.get("a_crc"):
            valid_ids.add(a["a_crc"])
    if agent_id not in valid_ids:
        ids = [a.get("a_id", "") for a in agents]
        raise ValidationError(
            f"Agent '{agent_id}' not found. Available agents: {ids}"
        )


async def resolve_agent_id(client: "AdaptixClient", agent_id: str) -> str:
    """Validate agent and return the canonical a_id (internal ID).

    Accepts both a_id (internal) and a_crc (GUI-visible 8-char hex).
    Raises ValidationError if the agent is not found.

    Used by _helpers.exec_cmd to normalize identifiers.
    """
    agent_id = validate_agent_id(agent_id)
    agents = await client.list_agents_raw()
    for a in agents:
        aid  = a.get("a_id", "")
        acrc = a.get("a_crc", "")
        if agent_id in (aid, acrc):
            return aid  # always return canonical a_id
    ids = [a.get("a_id", "") for a in agents]
    raise ValidationError(
        f"Agent '{agent_id}' not found. Available agents: {ids}"
    )
