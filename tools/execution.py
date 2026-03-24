"""
tools/execution.py — Command execution and privilege tools.

Covers:
  - Native: shell, powershell, execute_raw, sleep, jobs (list/kill)
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tools._context  import ToolContext
from tools._helpers  import exec_cmd
from utils.validation import validate_nonempty
from utils.logging   import get_logger

log = get_logger("tools.execution")


def register_execution_tools(mcp: FastMCP, ctx: ToolContext) -> None:
    """Register execution tools: native commands."""

    async def _exec(agent_id: str, cmdline: str, args: dict) -> str:
        return await exec_cmd(ctx, agent_id, cmdline, args, log_name=cmdline.split()[0])

    # ── Native execution commands ──────────────────────────────────────────────

    @mcp.tool(description=(
        "Execute a command via cmd.exe (Windows) or /bin/sh (Linux).\n"
        "Args: command (required) — e.g. 'whoami /all' or 'ipconfig /all'"
    ))
    async def execute_shell(agent_id: str, command: str) -> str:
        command = validate_nonempty(command, "command")
        return await _exec(agent_id, f"shell {command}",
                           {"command": "shell", "cmd_params": command})

    @mcp.tool(description=(
        "Execute a PowerShell expression (Windows only).\n"
        "Args: command (required) — e.g. 'Get-LocalUser | Select Name,Enabled'"
    ))
    async def execute_powershell(agent_id: str, command: str) -> str:
        command = validate_nonempty(command, "command")
        return await _exec(agent_id, f"powershell {command}",
                           {"command": "powershell", "cmd_params": command})

    @mcp.tool(description=(
        "Execute a raw command string on an agent (AxScript engine).\n"
        "The cmdline is parsed exactly as if typed in the agent console.\n"
        "Use for advanced commands not covered by other tools."
    ))
    async def execute_raw(agent_id: str, cmdline: str) -> str:
        from services.task_service import TaskTimeoutError
        from utils.validation import resolve_agent_id
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        cmdline  = validate_nonempty(cmdline, "cmdline")
        log.info("tool.execute_raw", agent_id=agent_id, cmdline=cmdline[:80])
        try:
            task = await ctx.task_svc.run_raw_and_wait(
                agent_id=agent_id, cmdline=cmdline
            )
            if task.is_error:
                return f"[ERROR] {task.output}"
            return task.output or "(no output)"
        except TaskTimeoutError:
            return f"Timeout waiting for '{cmdline}' to complete."
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool(description=(
        "Change the agent's sleep interval and jitter.\n"
        "Args: sleep_seconds (INT), jitter_percent (INT, default 0)"
    ))
    async def set_agent_sleep(
        agent_id: str, sleep_seconds: int, jitter_percent: int = 0
    ) -> str:
        return await _exec(agent_id, f"sleep {sleep_seconds} {jitter_percent}",
                           {"command": "sleep", "sleep": str(sleep_seconds),
                            "jitter": jitter_percent})

    @mcp.tool(description="List long-running background jobs on an agent.")
    async def jobs_list(agent_id: str) -> str:
        return await _exec(agent_id, "jobs list",
                           {"command": "jobs", "subcommand": "list"})

    @mcp.tool(description=(
        "Kill a background job on an agent by task ID.\n"
        "Args: task_id (STRING) — from jobs_list output."
    ))
    async def jobs_kill(agent_id: str, task_id: str) -> str:
        task_id = validate_nonempty(task_id, "task_id")
        return await _exec(agent_id, f"jobs kill {task_id}",
                           {"command": "jobs", "subcommand": "kill", "task_id": task_id})
