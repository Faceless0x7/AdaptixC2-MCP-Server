"""
tools/agents.py — Agent management tools.

Tools for listing, inspecting, tagging, and removing agents,
and for querying teamserver listeners.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tools._context  import ToolContext
from utils.validation import validate_agent_id, validate_agent_exists
from utils.logging   import get_logger

log = get_logger("tools.agents")


def register_agent_tools(mcp: FastMCP, ctx: ToolContext) -> None:
    """Register agent management MCP tools."""

    @mcp.tool(description=(
        "List all active agents connected to the AdaptixC2 teamserver.\n"
        "Returns: OS, hostname, username, IP, process, sleep interval, elevation status."
    ))
    async def list_agents() -> str:
        agents = await ctx.agent_svc.list_agents()
        if not agents:
            return "No agents currently connected."
        lines = [f"Found {len(agents)} agent(s):\n"]
        for a in agents:
            lines.append(a.summary())
        return "\n".join(lines)

    @mcp.tool(description=(
        "Get detailed information about a specific agent by ID.\n"
        "Accepts both internal a_id and GUI-visible a_crc (8-char hex)."
    ))
    async def agent_info(agent_id: str) -> str:
        agent_id = validate_agent_id(agent_id)
        agent = await ctx.agent_svc.get_agent(agent_id)
        if agent is None:
            return f"Agent '{agent_id}' not found."
        return (
            f"Agent Details:\n"
            f"  ID:          {agent.id}\n"
            f"  Computer:    {agent.computer}\n"
            f"  Domain:      {agent.domain}\n"
            f"  Username:    {agent.username}\n"
            f"  Impersonated:{agent.impersonated}\n"
            f"  OS:          {agent.os_name} ({agent.os_desc})\n"
            f"  Arch:        {agent.arch}\n"
            f"  Process:     {agent.process} PID={agent.pid} TID={agent.tid}\n"
            f"  Elevated:    {agent.elevated}\n"
            f"  Internal IP: {agent.internal_ip}\n"
            f"  External IP: {agent.external_ip}\n"
            f"  Listener:    {agent.listener}\n"
            f"  Sleep:       {agent.sleep}s (jitter {agent.jitter}%)\n"
            f"  Tags:        {agent.tags or 'none'}\n"
        )

    @mcp.tool(description=(
        "Remove an agent session from the teamserver.\n"
        "This removes the C2 record — it does NOT kill the implant process."
    ))
    async def kill_agent(agent_id: str) -> str:
        agent_id = validate_agent_id(agent_id)
        await validate_agent_exists(ctx.client, agent_id)
        await ctx.agent_svc.remove_agent(agent_id)
        log.info("tool.kill_agent", agent_id=agent_id)
        return f"Agent '{agent_id}' removed from the teamserver."

    @mcp.tool(description=(
        "Set a text tag on one or more agents for organisation.\n"
        "agent_ids: comma-separated list of agent IDs."
    ))
    async def tag_agent(agent_ids: str, tag: str) -> str:
        ids = [i.strip() for i in agent_ids.split(",") if i.strip()]
        if not ids:
            return "Error: provide at least one agent_id."
        await ctx.client.agent_set_tag(ids, tag)
        return f"Tag '{tag}' applied to agents: {', '.join(ids)}"

    @mcp.tool(description="List all active listeners on the teamserver.")
    async def list_listeners() -> str:
        listeners = await ctx.client.list_listeners_raw()
        if not listeners:
            return "No listeners currently active."
        lines = [f"Found {len(listeners)} listener(s):\n"]
        for l_ in listeners:
            name   = l_.get("l_name", "?")
            ltype  = l_.get("l_type", "?")
            proto  = l_.get("l_protocol", "?")
            addr   = l_.get("l_agent_addr", "?")
            status = l_.get("l_status", "?")
            lines.append(f"  [{proto}/{ltype}] {name}  @ {addr}  [{status}]")
        return "\n".join(lines)

    @mcp.tool(description=(
        "Show execution history for a specific agent.\n"
        "Returns recent commands, their timestamps, statuses and outputs.\n"
        "Use this to avoid repeating commands if results are recent and valid."
    ))
    async def list_task_history(agent_id: str, limit: int = 20) -> str:
        from models.task import Task
        import datetime

        agent_id = validate_agent_id(agent_id)
        tasks_raw = await ctx.client.list_tasks(agent_id, limit=limit)
        if not tasks_raw:
            return f"No task history found for agent '{agent_id}'."

        lines = [f"Recent task history for agent {agent_id} (last {len(tasks_raw)}):\n"]
        for t_raw in tasks_raw:
            try:
                t = Task.model_validate(t_raw)
                dt = datetime.datetime.fromtimestamp(t.start_time).strftime('%H:%M:%S')
                status = "SUCCESS" if t.completed and not t.is_error else ("ERROR" if t.is_error else "PENDING")
                
                # Truncate output preview for LLM context efficiency
                out_preview = t.output.strip().replace("\n", " ")
                if len(out_preview) > 120:
                    out_preview = out_preview[:120] + "..."
                
                lines.append(f"  [{dt}] [{status}] {t.command_line} -> {out_preview}")
            except Exception:
                continue

        return "\n".join(lines)
