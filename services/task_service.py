"""
AdaptixC2 MCP — Task Service
Handles task execution and polling for results.
"""

from __future__ import annotations

import asyncio
from typing import Optional, Any

from client.adaptix_client import AdaptixClient
from models.task import Task
from config import Config
from utils.logging import get_logger

log = get_logger("task_service")


class TaskTimeoutError(Exception):
    """Raised when polling for a task result exceeds the timeout."""


class TaskService:
    """
    High-level task management service.
    Handles issuing commands and polling until results are available.
    """

    def __init__(self, client: AdaptixClient) -> None:
        self._client = client

    async def _get_agent_name(self, agent_id: str) -> str:
        """Look up the agent type name (e.g., 'beacon') from the API."""
        try:
            agents = await self._client.list_agents_raw()
            for a in agents:
                if a.get("a_id") == agent_id:
                    return a.get("a_name", "beacon")
        except Exception:
            pass
        return "beacon"  # safe default

    async def run_command_and_wait(
        self,
        agent_id: str,
        cmdline: str,
        args: dict[str, Any],
        timeout: Optional[int] = None,
        agent_name: str = "",
    ) -> Task:
        """
        Execute a command on an agent and poll until a completed task appears.
        Returns the completed Task with its output.

        Strategy:
        1. Snapshot current task IDs before issuing the command
        2. Issue the command (fire-and-forget, not wait_answer)
        3. Poll GET /agent/task/list until a new completed task appears

        Note: wait_answer=True causes the HTTP request to block until the agent
        responds, which often times out for slow agents. Instead we poll.
        """
        poll_timeout  = timeout or Config.TASK_POLL_TIMEOUT
        poll_interval = Config.TASK_POLL_INTERVAL

        # Auto-resolve agent name if not provided
        if not agent_name:
            agent_name = await self._get_agent_name(agent_id)

        # Snapshot existing task IDs to detect the new one
        existing = await self._client.list_tasks(agent_id, limit=100)
        existing_ids = {t.get("a_task_id", "") for t in existing}

        log.info("task.execute", agent_id=agent_id, cmdline=cmdline, agent_name=agent_name)

        # Issue command — fire and forget (wait_answer=False)
        await self._client.agent_command_execute(
            agent_id=agent_id,
            agent_name=agent_name,
            cmdline=cmdline,
            args=args,
            wait_answer=False,
        )

        # Poll for a newly completed task
        deadline = asyncio.get_event_loop().time() + poll_timeout
        while asyncio.get_event_loop().time() < deadline:
            async with self._client.ws_cond:
                try:
                    await asyncio.wait_for(self._client.ws_cond.wait(), timeout=poll_interval)
                except asyncio.TimeoutError:
                    pass  # Wake up on timeout to poll API anyway

            tasks_raw = await self._client.list_tasks(agent_id, limit=100)
            for t_raw in tasks_raw:
                tid = t_raw.get("a_task_id", "")
                if tid and tid not in existing_ids:
                    completed = t_raw.get("a_completed", False)
                    if completed:
                        task = Task.model_validate(t_raw)
                        log.info("task.completed", agent_id=agent_id, task_id=tid, 
                                 is_error=task.is_error, cmdline=cmdline)
                        return task

        log.error("task.timeout", agent_id=agent_id, cmdline=cmdline, timeout=poll_timeout)
        raise TaskTimeoutError(
            f"Task '{cmdline}' on agent '{agent_id}' did not complete "
            f"within {poll_timeout}s"
        )


    async def run_raw_and_wait(
        self, agent_id: str, cmdline: str, timeout: Optional[int] = None
    ) -> Task:
        """
        Execute a raw cmdline (parsed by AxScript) and wait for results.
        Uses the same polling strategy as run_command_and_wait.
        """
        poll_timeout  = timeout or Config.TASK_POLL_TIMEOUT
        poll_interval = Config.TASK_POLL_INTERVAL

        existing = await self._client.list_tasks(agent_id, limit=100)
        existing_ids = {t.get("a_task_id", "") for t in existing}

        log.info("task.raw_execute", agent_id=agent_id, cmdline=cmdline)
        await self._client.agent_command_raw(agent_id=agent_id, cmdline=cmdline)

        deadline = asyncio.get_event_loop().time() + poll_timeout
        while asyncio.get_event_loop().time() < deadline:
            async with self._client.ws_cond:
                try:
                    await asyncio.wait_for(self._client.ws_cond.wait(), timeout=poll_interval)
                except asyncio.TimeoutError:
                    pass
                    
            tasks_raw = await self._client.list_tasks(agent_id, limit=100)
            for t_raw in tasks_raw:
                tid = t_raw.get("a_task_id", "")
                if tid and tid not in existing_ids:
                    completed = t_raw.get("a_completed", False)
                    if completed:
                        task = Task.model_validate(t_raw)
                        log.info("task.raw_completed", agent_id=agent_id, task_id=tid, cmdline=cmdline)
                        return task

        log.error("task.raw_timeout", agent_id=agent_id, cmdline=cmdline, timeout=poll_timeout)
        raise TaskTimeoutError(
            f"Raw task '{cmdline}' on agent '{agent_id}' did not complete "
            f"within {poll_timeout}s"
        )
