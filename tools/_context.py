"""
tools/_context.py — Dependency injection container for MCP tools.

ToolContext is built once in server.py and injected into every
tool registration function, replacing per-call service instantiation.
"""
from __future__ import annotations
from dataclasses import dataclass

from client.adaptix_client import AdaptixClient
from services.task_service  import TaskService
from services.agent_service import AgentService
from services.reporting_service import ReportingService


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Immutable container of shared, pre-built service instances."""
    client:     AdaptixClient
    task_svc:   TaskService
    agent_svc:  AgentService
    report_svc: ReportingService

    @classmethod
    def build(cls, client: AdaptixClient) -> "ToolContext":
        """Factory: construct all services from a single AdaptixClient."""
        return cls(
            client     = client,
            task_svc   = TaskService(client),
            agent_svc  = AgentService(client),
            report_svc = ReportingService(),
        )
