"""
tools/_helpers.py — Shared execution and tool registration utilities.

Key exported functions:
  exec_cmd() — native beacon command execution
"""
from __future__ import annotations



from services.task_service import TaskTimeoutError
from utils.logging         import get_logger
from utils.validation      import resolve_agent_id

from tools._context import ToolContext

log = get_logger(__name__)


# ── Shared execution paths ─────────────────────────────────────────────────────

async def exec_cmd(
    ctx: ToolContext,
    agent_id: str,
    cmdline: str,
    args: dict[str, str],
    log_name: str,
) -> str:
    """Shared execution path for native beacon commands."""
    agent_id = await resolve_agent_id(ctx.client, agent_id)
    log.info(f"tool.{log_name}", agent_id=agent_id, cmdline=cmdline[:80])
    try:
        task = await ctx.task_svc.run_command_and_wait(
            agent_id=agent_id,
            cmdline=cmdline,
            args=args,
        )
        if task.is_error:
            return f"[ERROR] {task.output}"
        return task.output or "(no output)"
    except TaskTimeoutError:
        return f"Timeout waiting for '{cmdline}' to complete."
    except Exception as e:
        return f"Error: {e}"
