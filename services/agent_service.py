"""
AdaptixC2 MCP — Agent Service
High-level agent operations for MCP tools.
"""

from __future__ import annotations

from typing import Optional

from client.adaptix_client import AdaptixClient
from models.agent import Agent
from utils.logging import get_logger

log = get_logger("agent_service")


class AgentService:
    """High-level agent management service."""

    def __init__(self, client: AdaptixClient):
        self._client = client

    async def list_agents(self) -> list[Agent]:
        """Return all live agents as typed Agent objects."""
        raw_list = await self._client.list_agents_raw()
        agents = []
        for raw in raw_list:
            try:
                agents.append(Agent.model_validate(raw))
            except Exception as e:
                log.warning("agent.parse_error", error=str(e), raw=str(raw)[:200])
        log.info("agent.list", count=len(agents))
        return agents

    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Look up a specific agent by ID."""
        agents = await self.list_agents()
        for a in agents:
            if a.id == agent_id:
                return a
        return None

    async def remove_agent(self, agent_id: str) -> None:
        """Remove/kill an agent session."""
        log.info("agent.remove", agent_id=agent_id)
        await self._client.remove_agent([agent_id])
