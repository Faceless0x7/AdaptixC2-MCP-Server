"""
mcp_tools/reporting.py — Reporting and findings tools.
"""
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from tools._context import ToolContext
from utils.validation import validate_agent_id

def register_reporting_tools(mcp: FastMCP, ctx: ToolContext) -> None:
    """Register MCP tools for reporting and logging findings."""

    @mcp.tool(description=(
        "Log a finding (credential, secret, or important file) to the local session notes.\n"
        "Arguments:\n"
        "  agent_id : STRING — ID of the agent where the finding was made.\n"
        "  category : STRING — Type of finding (e.g., 'Credential', 'Configuration', 'Loot').\n"
        "  content  : STRING — The actual data found (password, hash, file content).\n"
        "  context  : STRING — Description of where and how it was found."
    ))
    async def log_finding(agent_id: str, category: str, content: str, context: str = "") -> str:
        agent_id = validate_agent_id(agent_id)
        ctx.report_svc.add_finding(agent_id, category, content, context)
        return f"Finding logged to {ctx.report_svc.filepath}."

    @mcp.tool(description=(
        "Save a short writeup or explanation of an action (e.g., how you elevated privileges).\n"
        "Use this to record successful techniques for later review."
    ))
    async def save_writeup(agent_id: str, title: str, writeup: str) -> str:
        agent_id = validate_agent_id(agent_id)
        ctx.report_svc.add_writeup(agent_id, title, writeup)
        return f"Writeup '{title}' saved to {ctx.report_svc.filepath}."

    @mcp.tool(description="Read all saved notes and findings for this session.")
    async def view_session_notes() -> str:
        return ctx.report_svc.read_notes()
