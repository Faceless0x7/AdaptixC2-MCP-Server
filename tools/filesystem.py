"""
MCP Tools — Filesystem
Tools for file operations on agents.

Based on ax_config.axs (authoritative beacon command definitions):
  - cat  <path>              : Read first 2048 bytes of a file
  - cd   <path>              : Change working directory
  - cp   <src> <dst>         : Copy file
  - mv   <src> <dst>         : Move file
  - mkdir <path>             : Create directory
  - rm   <path>              : Remove file or folder
  - ls   [path]              : List directory (default ".")
  - pwd                      : Print working directory
  - download <file>          : Download file from agent to teamserver
  - upload <local> [remote]  : Upload file from teamserver to agent
  - disks                    : List mounted drives
"""

from __future__ import annotations
import base64

from mcp.server.fastmcp import FastMCP

from tools._context import ToolContext
from services.task_service import TaskTimeoutError
from utils.validation import validate_nonempty, resolve_agent_id
from utils.logging import get_logger

log = get_logger("tools.filesystem")


def register_filesystem_tools(mcp: FastMCP, ctx: ToolContext) -> None:
    """Register all filesystem MCP tools."""



    async def _run(agent_id: str, cmdline: str, args: dict) -> str:
        try:
            task = await ctx.task_svc.run_command_and_wait(
                agent_id=agent_id,
                cmdline=cmdline,
                args=args,
            )
            if task.is_error:
                return f"[ERROR] {task.output}"
            return task.output or "(no output)"
        except TaskTimeoutError as e:
            return f"Timeout: {e}"
        except Exception as e:
            return f"Error: {e}"

    @mcp.tool(
        description=(
            "List contents of a directory or details of a file on the agent.\n"
            "Usage: ls [path]\n"
            "Arguments:\n"
            "  path : STRING (optional, default '.') — Directory or file path to list.\n"
            "Example: ls C:\\\\Users"
        )
    )
    async def list_directory(agent_id: str, path: str = ".") -> str:
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.ls", agent_id=agent_id, path=path)
        return await _run(agent_id, f"ls {path}", {
            "command": "ls",
            "path": path,
            "message": "Task: list files",
        })

    @mcp.tool(
        description=(
            "Print the current working directory of the agent process.\n"
            "Usage: pwd\n"
            "Returns the absolute path of the agent's current directory."
        )
    )
    async def get_working_directory(agent_id: str) -> str:
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.pwd", agent_id=agent_id)
        return await _run(agent_id, "pwd", {"command": "pwd", "message": "Task: print working directory"})

    @mcp.tool(
        description=(
            "Read first 2048 bytes of a file on the agent.\n"
            "Usage: cat <path>\n"
            "Arguments:\n"
            "  path : STRING (required) — Absolute path to the file to read.\n"
            "Example: cat C:\\\\Windows\\\\System32\\\\drivers\\\\etc\\\\hosts"
        )
    )
    async def read_file(agent_id: str, path: str) -> str:
        path     = validate_nonempty(path, "path")
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.cat", agent_id=agent_id, path=path)
        return await _run(agent_id, f"cat {path}", {
            "command": "cat",
            "path": path,
            "message": "Task: read file",
        })

    @mcp.tool(
        description=(
            "Change the current working directory of the agent process.\n"
            "Usage: cd <path>\n"
            "Arguments:\n"
            "  path : STRING (required) — Target directory path.\n"
            "Example: cd C:\\\\Windows\\\\System32"
        )
    )
    async def change_directory(agent_id: str, path: str) -> str:
        path     = validate_nonempty(path, "path")
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.cd", agent_id=agent_id, path=path)
        return await _run(agent_id, f"cd {path}", {
            "command": "cd",
            "path": path,
            "message": "Task: change working directory",
        })

    @mcp.tool(
        description=(
            "Copy a file on the agent.\n"
            "Usage: cp <src> <dst>\n"
            "Arguments:\n"
            "  src : STRING (required) — Source file path.\n"
            "  dst : STRING (required) — Destination file path.\n"
            "Example: cp C:\\\\Temp\\\\file.txt C:\\\\Temp\\\\backup.txt"
        )
    )
    async def copy_file(agent_id: str, src: str, dst: str) -> str:
        src      = validate_nonempty(src, "src")
        dst      = validate_nonempty(dst, "dst")
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.cp", agent_id=agent_id, src=src, dst=dst)
        return await _run(agent_id, f"cp {src} {dst}", {
            "command": "cp",
            "src": src,
            "dst": dst,
            "message": "Task: copy file",
        })

    @mcp.tool(
        description=(
            "Move (rename) a file on the agent.\n"
            "Usage: mv <src> <dst>\n"
            "Arguments:\n"
            "  src : STRING (required) — Source file path.\n"
            "  dst : STRING (required) — Destination file path.\n"
            "Example: mv C:\\\\Temp\\\\old.txt C:\\\\Temp\\\\new.txt"
        )
    )
    async def move_file(agent_id: str, src: str, dst: str) -> str:
        src      = validate_nonempty(src, "src")
        dst      = validate_nonempty(dst, "dst")
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.mv", agent_id=agent_id, src=src, dst=dst)
        return await _run(agent_id, f"mv {src} {dst}", {
            "command": "mv",
            "src": src,
            "dst": dst,
            "message": "Task: move file",
        })

    @mcp.tool(
        description=(
            "Create a directory on the agent.\n"
            "Usage: mkdir <path>\n"
            "Arguments:\n"
            "  path : STRING (required) — Directory path to create.\n"
            "Example: mkdir C:\\\\Temp\\\\newdir"
        )
    )
    async def make_directory(agent_id: str, path: str) -> str:
        path     = validate_nonempty(path, "path")
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.mkdir", agent_id=agent_id, path=path)
        return await _run(agent_id, f"mkdir {path}", {
            "command": "mkdir",
            "path": path,
            "message": "Task: make directory",
        })

    @mcp.tool(
        description=(
            "Remove a file or folder on the agent.\n"
            "Usage: rm <path>\n"
            "Arguments:\n"
            "  path : STRING (required) — Path to file or directory to remove.\n"
            "Example: rm C:\\\\Temp\\\\file.txt"
        )
    )
    async def remove_file(agent_id: str, path: str) -> str:
        path     = validate_nonempty(path, "path")
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.rm", agent_id=agent_id, path=path)
        return await _run(agent_id, f"rm {path}", {
            "command": "rm",
            "path": path,
            "message": "Task: remove file or directory",
        })

    @mcp.tool(
        description=(
            "Task the agent to download a file to the teamserver.\n"
            "Usage: download <file>\n"
            "Arguments:\n"
            "  remote_path : STRING (required) — Full path to the file on the agent to download.\n"
            "Example: download C:\\\\Temp\\\\secrets.txt\n"
            "Use list_downloads to see completed downloads and get_downloaded_file to retrieve content."
        )
    )
    async def download_file(agent_id: str, remote_path: str) -> str:
        agent_id    = validate_agent_id(agent_id)
        remote_path = validate_nonempty(remote_path, "remote_path")
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.download", agent_id=agent_id, path=remote_path)
        return await _run(agent_id, f"download {remote_path}", {
            "command": "download",
            "file": remote_path,
            "message": "Task: download file",
        })

    @mcp.tool(
        description=(
            "List mounted drives on the agent system.\n"
            "Usage: disks\n"
            "Returns: list of mounted drives (e.g. C:\\\\, D:\\\\)."
        )
    )
    async def list_disks(agent_id: str) -> str:
        agent_id = await resolve_agent_id(ctx.client, agent_id)
        log.info("tool.disks", agent_id=agent_id)
        return await _run(agent_id, "disks", {"command": "disks", "message": "Task: show mounted disks"})

    @mcp.tool(
        description=(
            "List all files that have been downloaded from agents to the teamserver."
        )
    )
    async def list_downloads() -> str:
        downloads = await ctx.client.list_downloads_raw()
        if not downloads:
            return "No downloads available."
        lines = [f"Found {len(downloads)} download(s):"]
        for d in downloads:
            fid   = d.get("FileId", d.get("file_id", "?"))
            fname = d.get("FileName", d.get("file_name", "?"))
            size  = d.get("FileSize", d.get("file_size", 0))
            agent = d.get("AgentId", d.get("agent_id", "?"))
            lines.append(f"  [{fid}] {fname} ({size} bytes) from agent {agent}")
        return "\n".join(lines)

    @mcp.tool(
        description=(
            "Retrieve the content of a file previously downloaded from an agent.\n"
            "Returns the file content as base64-encoded text.\n"
            "Use list_downloads to get file IDs."
        )
    )
    async def get_downloaded_file(file_id: str) -> str:
        file_id = validate_nonempty(file_id, "file_id")
        log.info("tool.sync_download", file_id=file_id)
        try:
            filename, content = await ctx.client.sync_download(file_id)
            b64 = base64.b64encode(content).decode()
            return (
                f"File: {filename}\n"
                f"Size: {len(content)} bytes\n"
                f"Content (base64):\n{b64}"
            )
        except Exception as e:
            return f"Error syncing download: {e}"
