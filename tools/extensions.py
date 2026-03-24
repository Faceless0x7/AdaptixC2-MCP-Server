"""
tools/extensions.py — Wrappers for Extension-Kit BOF tools (Dynamically Configured).
"""
from __future__ import annotations

import os
import yaml
from mcp.server.fastmcp import FastMCP

from tools._context import ToolContext
from utils.validation import validate_nonempty
from utils.logging import get_logger
from services.task_service import TaskTimeoutError
from utils.validation import resolve_agent_id

log = get_logger("tools.extensions")

CATEGORIES = {
    "AD-BOF": {
        "desc": "Active Directory Exploitation commands.",
        "cmds": ["adwssearch", "badtakeover", "dcsync single", "dcsync all", "ldapsearch", "ldapq computers", "readlaps", "webdav enable", "webdav status"]
    },
    "ADCS-BOF": {
        "desc": "Active Directory Certificate Services commands.",
        "cmds": ["certi auth", "certi enum", "certi request", "certi request_on_behalf", "certi shadow"]
    },
    "Creds-BOF": {
        "desc": "Windows credential extraction commands.",
        "cmds": ["askcreds", "get-netntlm", "hashdump", "cookie-monster", "nanodump", "nanodump_ppl_dump", "nanodump_ppl_medic", "nanodump_ssp", "underlaycopy", "lsadump_secrets", "lsadump_sam", "lsadump_cache"]
    },
    "Elevation-BOF": {
        "desc": "Privilege escalation commands.",
        "cmds": ["getsystem token", "uacbybass sspi", "uacbybass regshellcmd", "potato-dcom", "potato-print"]
    },
    "Execution-BOF": {
        "desc": "Execute in-memory payloads.",
        "cmds": ["execute-assembly", "noconsolation"]
    },
    "Injection-BOF": {
        "desc": "Process injection techniques.",
        "cmds": ["inject-cfg", "inject-sec", "inject-poolparty", "inject-32to64"]
    },
    "Kerbeus-BOF": {
        "desc": "Kerberos abuse and ticket manipulation.",
        "cmds": ["kerbeus asreproasting", "kerbeus asktgt", "kerbeus asktgs", "kerbeus changepw", "kerbeus dump", "kerbeus hash", "kerbeus kerberoasting", "kerbeus klist", "kerbeus ptt", "kerbeus describe", "kerbeus purge", "kerbeus renew", "kerbeus s4u", "kerbeus cross_s4u", "kerbeus tgtdeleg", "kerbeus triage"]
    },
    "LDAP-BOF": {
        "desc": "LDAP querying and manipulation.",
        "cmds": ["ldap get-acl", "ldap get-attribute", "ldap get-computers", "ldap get-groups", "ldap get-groupmembers", "ldap get-delegation", "ldap get-domaininfo", "ldap get-maq", "ldap get-object", "ldap get-rbcd", "ldap get-spn", "ldap get-uac", "ldap get-users", "ldap get-usergroups", "ldap get-writable", "ldap move-object", "ldap add-ace", "ldap add-attribute", "ldap add-computer", "ldap add-delegation", "ldap add-group", "ldap add-groupmember", "ldap add-ou", "ldap add-rbcd", "ldap add-sidhistory", "ldap add-spn", "ldap add-user", "ldap add-uac", "ldap add-genericall", "ldap add-genericwrite", "ldap add-dcsync", "ldap add-asreproastable", "ldap add-unconstrained", "ldap add-constrained", "ldap set-attribute", "ldap set-delegation", "ldap set-owner", "ldap set-spn", "ldap set-password", "ldap set-uac", "ldap remove-ace", "ldap remove-attribute", "ldap remove-delegation", "ldap remove-dcsync", "ldap remove-genericall", "ldap remove-genericwrite", "ldap remove-groupmember", "ldap remove-object", "ldap remove-rbcd", "ldap remove-spn", "ldap remove-uac"]
    },
    "LateralMovement": {
        "desc": "Lateral movement execution commands.",
        "cmds": ["jump psexec", "jump scshell", "invoke winrm", "invoke scshell", "token make", "token steal", "runas-user", "runas-session"]
    },
    "MSSQL-BOF": {
        "desc": "MS SQL Server enumeration and exploitation.",
        "cmds": ["mssql 1434udp", "mssql adsi", "mssql agentcmd", "mssql agentstatus", "mssql checkrpc", "mssql clr", "mssql columns", "mssql databases", "mssql disableclr", "mssql disableole", "mssql disablerpc", "mssql disablexp", "mssql enableclr", "mssql enableole", "mssql enablerpc", "mssql enablexp", "mssql impersonate", "mssql info", "mssql links", "mssql olecmd", "mssql query", "mssql rows", "mssql search", "mssql smb", "mssql tables", "mssql users", "mssql whoami", "mssql xpcmd"]
    },
    "PostEx-BOF": {
        "desc": "Post-exploitation data collection and persistence.",
        "cmds": ["firewallrule add", "screenshot_bof", "sauroneye"]
    },
    "Process-BOF": {
        "desc": "Process enumeration and manipulation.",
        "cmds": ["findobj module", "findobj prochandle", "process conn", "procfreeze freeze", "procfreeze unfreeze"]
    },
    "RelayInformer-BOF": {
        "desc": "Check for relaying vulnerability enforcement.",
        "cmds": ["relay-informer http", "relay-informer ldap", "relay-informer mssql", "relay-informer smb"]
    },
    "SAL-BOF": {
        "desc": "Situational Awareness Local (Windows host commands).",
        "cmds": ["arp", "cacls", "dir", "env", "ipconfig", "listdns", "netstat", "nslookup", "privcheck all", "privcheck alwayselevated", "privcheck autologon", "privcheck credmanager", "privcheck hijackablepath", "privcheck modautorun", "privcheck modsvc", "privcheck tokenpriv", "privcheck unattendfiles", "privcheck unquotedsvc", "privcheck pshistory", "privcheck uacstatus", "privcheck vulndrivers", "routeprint", "uptime", "useridletime", "whoami"]
    },
    "SAR-BOF": {
        "desc": "Situational Awareness Remote (Network discovery commands).",
        "cmds": ["smartscan", "taskhound", "quser", "nbtscan"]
    }
}

def load_bof_config() -> dict:
    # Look for bofs.yaml in the project root
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bofs.yaml")
    if not os.path.isfile(config_path):
        log.warning("bofs.yaml not found, loading all BOFs by default.")
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        log.error("bofs.yaml_parse_error", error=str(e))
        return {}

def register_extensions_tools(mcp: FastMCP, ctx: ToolContext) -> None:
    """Register BOF extension tools dynamically based on configuration."""

    bof_config = load_bof_config()

    async def _exec_bof(agent_id: str, cmdline: str) -> str:
        """Helper to run the command string representing a BOF invocation."""
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        cmdline = validate_nonempty(cmdline, "cmdline")
        log.info("tool.exec_bof", agent_id=agent_id, cmdline=cmdline[:80])
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

    for cat_name, cat_data in CATEGORIES.items():
        base_desc = cat_data["desc"]
        all_cmds = cat_data["cmds"]
        
        # Determine allowed commands
        if cat_name not in bof_config:
            continue # Category is disabled (missing from YAML)
        rule = bof_config[cat_name]
        if not rule:
            continue # Disabled (null)
        elif isinstance(rule, str) and rule.lower() == "all":
            allowed = all_cmds
        elif isinstance(rule, list):
            allowed = [c for c in all_cmds if c in rule]
        else:
            continue
                
        if not allowed:
            continue

        # Format description so the LLM knows exactly what is available
        desc = (
            f"{cat_name}: {base_desc}\n"
            f"Commands: {', '.join(allowed)}.\n"
            "Args: command (str), args (str)."
        )
        
        def create_tool(c_name: str, allowed_cmds: list[str]):
            async def bof_tool(agent_id: str, command: str, args: str = "") -> str:
                # Runtime validation to enforce config limits
                if command not in allowed_cmds:
                    return f"[ERROR] Command '{command}' is not allowed by bofs.yaml configuration."
                cmdline = f"{command} {args}".strip()
                return await _exec_bof(agent_id, cmdline)
            
            tool_name = f"bof_{c_name.lower().replace('-', '')}"
            bof_tool.__name__ = tool_name
            return bof_tool
            
        handler = create_tool(cat_name, allowed)
        # Add the tool dynamically to MCP
        mcp.tool(description=desc, name=handler.__name__)(handler)
        log.info("bof.registered", category=cat_name, allowed_count=len(allowed))
