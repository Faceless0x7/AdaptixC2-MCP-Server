"""
MCP Tools — Networking
Tools for tunnel management (SOCKS, port forwarding).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tools._context import ToolContext
from client.adaptix_client import AdaptixAPIError
from utils.validation import validate_port, validate_nonempty, resolve_agent_id
from utils.logging import get_logger

log = get_logger("tools.networking")


def register_networking_tools(mcp: FastMCP, ctx: ToolContext) -> None:
    """Register all networking/tunnel MCP tools."""

    @mcp.tool(description="List all active tunnels (SOCKS proxies, port forwards) on the teamserver.")
    async def list_tunnels() -> str:
        tunnels = await ctx.client.list_tunnels_raw()
        if not tunnels:
            return "No active tunnels."
        lines = [f"Found {len(tunnels)} tunnel(s):"]
        for t in tunnels:
            tid   = t.get("TunnelId", t.get("tunnel_id", "?"))
            ttype = t.get("Type", t.get("type", "?"))
            lhost = t.get("Lhost", t.get("lhost", ""))
            lport = t.get("Lport", t.get("lport", ""))
            agent = t.get("AgentId", t.get("agent_id", "?"))
            info  = t.get("Info", t.get("info", ""))
            lines.append(f"  [{tid}] Type={ttype} {lhost}:{lport} Agent={agent} Info={info!r}")
        return "\n".join(lines)

    @mcp.tool(
        description=(
            "Start a SOCKS5 proxy tunnel through an agent. "
            "Binds a SOCKS5 listener on the teamserver host. "
            "Returns the tunnel ID on success."
        )
    )
    async def start_socks5(
        agent_id: str,
        lhost: str,
        lport: int,
        description: str = "",
        use_auth: bool = False,
        socks_username: str = "",
        socks_password: str = "",
    ) -> str:
        lhost    = validate_nonempty(lhost, "lhost")
        lport    = validate_port(lport, "lport")
        agent_id = await resolve_agent_id(ctx.client, agent_id)

        log.info("tool.socks5", agent_id=agent_id, lhost=lhost, lport=lport)
        try:
            tunnel_id = await ctx.client.start_socks5(
                agent_id=agent_id, lhost=lhost, lport=lport,
                desc=description, listen=True,
                use_auth=use_auth, username=socks_username, password=socks_password,
            )
            return f"SOCKS5 tunnel started. Tunnel ID: {tunnel_id}\nProxy: socks5://{lhost}:{lport}"
        except AdaptixAPIError as e:
            return f"Failed to start SOCKS5: {e}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool(
        description=(
            "Start a SOCKS4 proxy tunnel through an agent. "
            "Binds a SOCKS4 listener on the teamserver host. "
            "Returns the tunnel ID on success."
        )
    )
    async def start_socks4(
        agent_id: str, lhost: str, lport: int, description: str = ""
    ) -> str:
        lhost    = validate_nonempty(lhost, "lhost")
        lport    = validate_port(lport, "lport")
        agent_id = await resolve_agent_id(ctx.client, agent_id)

        log.info("tool.socks4", agent_id=agent_id, lhost=lhost, lport=lport)
        try:
            tunnel_id = await ctx.client.start_socks4(
                agent_id=agent_id, lhost=lhost, lport=lport, desc=description
            )
            return f"SOCKS4 tunnel started. Tunnel ID: {tunnel_id}\nProxy: socks4://{lhost}:{lport}"
        except AdaptixAPIError as e:
            return f"Failed to start SOCKS4: {e}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool(
        description=(
            "Start a local port forward through an agent: "
            "lhost:lport (local on teamserver) → thost:tport (target via agent). "
            "Returns the tunnel ID."
        )
    )
    async def port_forward(
        agent_id: str,
        lhost: str,
        lport: int,
        target_host: str,
        target_port: int,
        description: str = "",
    ) -> str:
        lhost       = validate_nonempty(lhost, "lhost")
        lport       = validate_port(lport, "lport")
        target_host = validate_nonempty(target_host, "target_host")
        target_port = validate_port(target_port, "target_port")
        agent_id = await resolve_agent_id(ctx.client, agent_id)

        log.info("tool.lportfwd", agent_id=agent_id, lhost=lhost, lport=lport,
                 thost=target_host, tport=target_port)
        try:
            tunnel_id = await ctx.client.start_lportfwd(
                agent_id=agent_id, lhost=lhost, lport=lport,
                thost=target_host, tport=target_port, desc=description,
            )
            return (
                f"Local port forward started. Tunnel ID: {tunnel_id}\n"
                f"Route: {lhost}:{lport} → {target_host}:{target_port}"
            )
        except AdaptixAPIError as e:
            return f"Failed: {e}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool(
        description=(
            "Start a reverse port forward through an agent: "
            "agent listens on port, forwards to thost:tport from the teamserver. "
            "Returns the tunnel ID."
        )
    )
    async def reverse_port_forward(
        agent_id: str,
        port: int,
        target_host: str,
        target_port: int,
        description: str = "",
    ) -> str:
        port        = validate_port(port, "port")
        target_host = validate_nonempty(target_host, "target_host")
        target_port = validate_port(target_port, "target_port")
        agent_id = await resolve_agent_id(ctx.client, agent_id)

        log.info("tool.rportfwd", agent_id=agent_id, port=port,
                 thost=target_host, tport=target_port)
        try:
            tunnel_id = await ctx.client.start_rportfwd(
                agent_id=agent_id, port=port,
                thost=target_host, tport=target_port, desc=description,
            )
            return (
                f"Reverse port forward started. Tunnel ID: {tunnel_id}\n"
                f"Agent port: {port} → {target_host}:{target_port}"
            )
        except AdaptixAPIError as e:
            return f"Failed: {e}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool(description="Stop an active tunnel by its ID. Use list_tunnels to find tunnel IDs.")
    async def stop_tunnel(tunnel_id: str) -> str:
        tunnel_id = validate_nonempty(tunnel_id, "tunnel_id")
        log.info("tool.stop_tunnel", tunnel_id=tunnel_id)
        try:
            await ctx.client.stop_tunnel(tunnel_id)
            return f"Tunnel '{tunnel_id}' stopped."
        except AdaptixAPIError as e:
            return f"Failed to stop tunnel: {e}"
        except Exception as e:
            return f"Error: {e}"
