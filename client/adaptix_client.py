"""
AdaptixC2 MCP — Async REST Client
Wraps all Adaptix REST endpoints with auto token refresh.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from typing import Any, Optional

import httpx

from config import Config
from utils.logging import get_logger

# Silence httpx's own transport-level logging — it writes to stdout
# which would corrupt the MCP JSON-RPC stdio stream.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

log = get_logger("adaptix_client")


class AdaptixAPIError(Exception):
    """Raised when the Adaptix API returns ok=false."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AdaptixClient:
    """
    Async HTTP client for the AdaptixC2 REST API.
    Handles login, JWT refresh, and all known endpoints.
    """

    def __init__(self) -> None:
        self._base_url = Config.base_url()
        self._username = Config.USERNAME
        self._password = Config.PASSWORD

        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: float = 0.0   # Unix timestamp

        self._client: Optional[httpx.AsyncClient] = None
        self._started: bool = False
        self._refreshing: bool = False
        self.ws_cond = asyncio.Condition()
        # NOTE: no asyncio.Lock here — creating asyncio primitives before the
        # event loop starts (i.e. before anyio.run / mcp.run) causes subtle
        # failures in Python 3.13. MCP stdio is single-threaded so no lock needed.

    # ── Lifecycle ──────────────────────────────────────────────────────────

    async def __aenter__(self) -> "AdaptixClient":
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def start(self) -> None:
        """Create the underlying httpx client and authenticate."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            verify=Config.VERIFY_SSL,
            timeout=60.0,
        )
        await self.login()
        self._started = True

    async def _ensure_started(self) -> None:
        """Lazily start and authenticate if not yet done."""
        if not self._started:
            await self.start()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            self._started = False

    # ── Authentication ─────────────────────────────────────────────────────

    async def login(self) -> None:
        """Authenticate and store tokens."""
        payload = {
            "username": self._username,
            "password": self._password,
            "version":  "1.0",
        }
        resp = await self._raw_post("/login", payload)
        if "access_token" not in resp or "refresh_token" not in resp:
            raise AdaptixAPIError("Login failed: no tokens in response")

        self._access_token  = resp["access_token"]
        self._refresh_token = resp["refresh_token"]
        # Decode expiry from JWT (exp claim), fallback to 10 minutes
        self._token_expiry = self._parse_jwt_exp(self._access_token) or (time.time() + 600)
        log.info("login.success", username=self._username)

    async def _refresh(self) -> None:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            await self.login()
            return
        headers = {"Authorization": f"Bearer {self._refresh_token}"}
        if self._client is None:
            raise RuntimeError("Client not started")
        r = await self._client.post("/refresh", json={}, headers=headers)
        r.raise_for_status()
        data = r.json()
        if "access_token" in data:
            self._access_token = data["access_token"]
            self._token_expiry = self._parse_jwt_exp(self._access_token) or (time.time() + 600)
            log.info("token.refreshed")
        else:
            log.warning("token.refresh_failed", falling_back="re-login")
            await self.login()

    async def _ensure_token(self) -> None:
        """Ensure the access token is valid, refreshing if necessary."""
        margin = Config.TOKEN_REFRESH_MARGIN
        if time.time() >= (self._token_expiry - margin):
            if not self._refreshing:
                self._refreshing = True
                try:
                    await self._refresh()
                finally:
                    self._refreshing = False

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    @staticmethod
    def _parse_jwt_exp(token: str) -> Optional[float]:
        """Extract the 'exp' claim from a JWT without verification."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            padded = parts[1] + "=" * (-len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            exp = payload.get("exp")
            return float(exp) if exp else None
        except Exception:
            return None

    # ── Low-level helpers ──────────────────────────────────────────────────

    async def _raw_post(self, path: str, payload: Any) -> dict:
        """POST without auth header (for login/refresh)."""
        if self._client is None:
            raise RuntimeError("Client not started — call start() first")
        r = await self._client.post(path, json=payload)
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, payload: Any = None) -> dict:
        """Authenticated POST, raises AdaptixAPIError on ok=false."""
        await self._ensure_started()
        await self._ensure_token()
        if self._client is None:
            raise RuntimeError("Client not started")
        r = await self._client.post(path, json=payload or {}, headers=self._headers())
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and data.get("ok") is False:
            raise AdaptixAPIError(data.get("message", "Unknown error"))
        return data

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """Authenticated GET, returns parsed JSON (dict or list)."""
        await self._ensure_started()
        await self._ensure_token()
        if self._client is None:
            raise RuntimeError("Client not started")
        r = await self._client.get(path, params=params or {}, headers=self._headers())
        r.raise_for_status()
        # List endpoints return raw JSON arrays
        return r.json()

    async def _get_bytes(self, path: str, params: Optional[dict] = None) -> bytes:
        """Authenticated GET returning raw bytes (screenshots, files)."""
        await self._ensure_started()
        await self._ensure_token()
        if self._client is None:
            raise RuntimeError("Client not started")
        r = await self._client.get(path, params=params or {}, headers=self._headers())
        r.raise_for_status()
        return r.content

    # ── OTP ─────────────────────────────────────────────────────────────────

    async def generate_otp(self, otp_type: str, data: dict) -> str:
        """Generate a short-lived OTP token for WebSocket connect or file ops."""
        result = await self._post("/otp/generate", {"type": otp_type, "data": data})
        return result["message"]

    async def get_connect_otp(
        self,
        subscriptions: Optional[list[str]] = None,
        client_type: int = 3,
        console_team_mode: bool = False,
    ) -> str:
        """Generate an OTP for WebSocket /connect."""
        data = {
            "client_type": client_type,
            "console_team_mode": console_team_mode,
            "subscriptions": subscriptions or [],
        }
        return await self.generate_otp("connect", data)

    async def ws_connect_operator(self) -> None:
        """Open a persistent WebSocket /connect to AdaptixC2.

        This makes the MCP operator name appear in the teamserver GUI
        (connect/disconnect events), exactly like a real GUI client.
        Reconnects automatically on disconnect.
        """
        import ssl as ssl_mod
        import websockets

        ws_base = Config.ws_url()      # e.g. wss://127.0.0.1:443/endpoint
        ssl_ctx: Optional[ssl_mod.SSLContext] = None
        if ws_base.startswith("wss://"):
            ssl_ctx = ssl_mod.create_default_context()
            if not Config.VERIFY_SSL:
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl_mod.CERT_NONE

        log.info("ws_operator.starting", username=Config.USERNAME)
        while True:
            try:
                otp = await self.get_connect_otp(
                    subscriptions=[],
                    client_type=3,          # 3 = operator/console
                    console_team_mode=False,
                )
                ws_url = f"{ws_base}/connect?otp={otp}"
                connect_kw: dict = {"ssl": ssl_ctx} if ssl_ctx else {}
                async with websockets.connect(ws_url, **connect_kw) as ws:
                    log.info("ws_operator.connected", username=Config.USERNAME)
                    
                    # AdaptixC2 ONLY broadcasts the "Operator connected" message to 
                    # the GUI when the client explicitly triggers a /sync after connecting.
                    await self.sync()
                    
                    # Keep the connection alive — teamserver pings/messages
                    async for _msg in ws:
                        async with self.ws_cond:
                            self.ws_cond.notify_all()
            except Exception as exc:
                log.warning("ws_operator.reconnecting", error=str(exc))
                await asyncio.sleep(5)  # brief pause before reconnect

    async def get_download_otp(self, file_id: str) -> str:
        return await self.generate_otp("download", {"id": file_id})

    async def get_upload_otp(self, file_id: str) -> str:
        return await self.generate_otp("tmp_upload", {"id": file_id})

    # ── Session/Sync ────────────────────────────────────────────────────────

    async def sync(self) -> None:
        """Trigger server-side sync for this client."""
        await self._post("/sync")

    async def subscribe(self, categories: list[str], console_team_mode: bool = False) -> None:
        """Update WebSocket event subscriptions."""
        await self._post("/subscribe", {
            "categories": categories,
            "console_team_mode": console_team_mode,
        })

    # ── Agents ──────────────────────────────────────────────────────────────

    async def list_agents_raw(self) -> list[dict]:
        """Return raw list of agent dicts."""
        data = await self._get("/agent/list")
        if isinstance(data, list):
            return data
        return []

    async def generate_agent(
        self, listener_names: list[str], agent_name: str, config: str
    ) -> tuple[str, bytes]:
        """
        Build an agent payload.
        Returns (filename, binary_content).
        """
        result = await self._post("/agent/generate", {
            "listener_name": listener_names,
            "agent": agent_name,
            "config": config,
        })
        encoded: str = result["message"]
        fname_b64, content_b64 = encoded.split(":", 1)
        filename = base64.b64decode(fname_b64).decode()
        content  = base64.b64decode(content_b64)
        return filename, content

    async def remove_agent(self, agent_ids: list[str]) -> None:
        await self._post("/agent/remove", {"agent_id_array": agent_ids})

    async def agent_command_execute(
        self,
        agent_id: str,
        cmdline: str,
        args: dict,
        agent_name: str = "beacon",
        ui: bool = False,         # False = command appears in console. True = hidden background task (e.g. file browser)
        hook_id: str = "",
        handler_id: str = "",
        wait_answer: bool = False,
    ) -> None:
        """Send a structured command to an agent.
        
        Both 'id' (agent ID) and 'name' (agent type, e.g. 'beacon') are required
        by the AdaptixC2 Go server's CommandData struct.
        """
        payload = {
            "id":             agent_id,
            "name":           agent_name,    # REQUIRED: agent type (e.g. "beacon")
            "cmdline":        cmdline,
            "data":           json.dumps(args),
            "ui":             ui,
            "ax_hook_id":     hook_id,
            "ax_handler_id":  handler_id,
            "wait_answer":    wait_answer,
        }
        await self._post("/agent/command/execute", payload)


    async def agent_command_raw(self, agent_id: str, cmdline: str) -> None:
        """Send a raw cmdline string (parsed by AxScript engine)."""
        await self._post("/agent/command/raw", {"id": agent_id, "cmdline": cmdline})

    async def agent_set_tag(self, agent_ids: list[str], tag: str) -> None:
        await self._post("/agent/set/tag", {"agent_id_array": agent_ids, "tag": tag})

    async def agent_set_mark(self, agent_ids: list[str], mark: str) -> None:
        await self._post("/agent/set/mark", {"agent_id_array": agent_ids, "mark": mark})

    async def agent_console_remove(self, agent_ids: list[str]) -> None:
        await self._post("/agent/console/remove", {"agent_id_array": agent_ids})

    # ── Tasks ───────────────────────────────────────────────────────────────

    async def list_tasks(
        self, agent_id: str, limit: int = 200, offset: int = 0
    ) -> list[dict]:
        data = await self._get("/agent/task/list", {
            "agent_id": agent_id,
            "limit":    limit,
            "offset":   offset,
        })
        if isinstance(data, list):
            return data
        return []

    async def cancel_task(self, agent_id: str, task_ids: list[str]) -> None:
        await self._post("/agent/task/cancel", {
            "agent_id":    agent_id,
            "tasks_array": task_ids,
        })

    async def delete_task(self, agent_id: str, task_ids: list[str]) -> None:
        await self._post("/agent/task/delete", {
            "agent_id":    agent_id,
            "tasks_array": task_ids,
        })

    # ── Listeners ────────────────────────────────────────────────────────────

    async def list_listeners_raw(self) -> list[dict]:
        data = await self._get("/listener/list")
        if isinstance(data, list):
            return data
        return []

    async def start_listener(self, name: str, config_type: str, config: str) -> None:
        await self._post("/listener/create", {
            "name":   name,
            "type":   config_type,
            "config": config,
        })

    async def stop_listener(self, name: str, config_type: str) -> None:
        await self._post("/listener/stop", {"name": name, "type": config_type})

    async def pause_listener(self, name: str, config_type: str) -> None:
        await self._post("/listener/pause", {"name": name, "type": config_type})

    async def resume_listener(self, name: str, config_type: str) -> None:
        await self._post("/listener/resume", {"name": name, "type": config_type})

    async def edit_listener(self, name: str, config_type: str, config: str) -> None:
        await self._post("/listener/edit", {
            "name":   name,
            "type":   config_type,
            "config": config,
        })

    # ── Downloads / Files ─────────────────────────────────────────────────

    async def list_downloads_raw(self) -> list[dict]:
        data = await self._get("/download/list")
        if isinstance(data, list):
            return data
        return []

    async def sync_download(self, file_id: str) -> tuple[str, bytes]:
        """Download a file. Returns (filename, content_bytes)."""
        result = await self._post("/download/sync", {"file_id": file_id})
        filename = result.get("filename", file_id)
        content  = base64.b64decode(result.get("content", ""))
        return filename, content

    async def delete_download(self, file_ids: list[str]) -> None:
        await self._post("/download/delete", {"file_id_array": file_ids})

    # ── Screenshots ──────────────────────────────────────────────────────

    async def list_screenshots_raw(self) -> list[dict]:
        data = await self._get("/screen/list")
        if isinstance(data, list):
            return data
        return []

    async def get_screenshot_image(self, screen_id: str) -> bytes:
        """Returns raw PNG bytes."""
        return await self._get_bytes("/screen/image", {"screen_id": screen_id})

    async def remove_screenshot(self, screen_ids: list[str]) -> None:
        await self._post("/screen/remove", {"screen_id_array": screen_ids})

    async def set_screenshot_note(self, screen_ids: list[str], note: str) -> None:
        await self._post("/screen/setnote", {"screen_id_array": screen_ids, "note": note})

    # ── Credentials ──────────────────────────────────────────────────────

    async def list_creds_raw(self) -> list[dict]:
        data = await self._get("/creds/list")
        if isinstance(data, list):
            return data
        return []

    async def add_creds(self, creds: list[dict]) -> None:
        await self._post("/creds/add", {"creds": creds})

    async def edit_cred(
        self, cred_id: str, username: str, password: str,
        realm: str = "", cred_type: str = "", tag: str = "",
        storage: str = "", host: str = "",
    ) -> None:
        await self._post("/creds/edit", {
            "cred_id":  cred_id,
            "username": username,
            "password": password,
            "realm":    realm,
            "type":     cred_type,
            "tag":      tag,
            "storage":  storage,
            "host":     host,
        })

    async def remove_creds(self, cred_ids: list[str]) -> None:
        await self._post("/creds/remove", {"cred_id_array": cred_ids})

    async def set_creds_tag(self, cred_ids: list[str], tag: str) -> None:
        await self._post("/creds/set/tag", {"id_array": cred_ids, "tag": tag})

    # ── Targets ──────────────────────────────────────────────────────────

    async def list_targets_raw(self) -> list[dict]:
        data = await self._get("/targets/list")
        if isinstance(data, list):
            return data
        return []

    async def add_targets(self, targets: list[dict]) -> None:
        await self._post("/targets/add", {"targets": targets})

    async def remove_targets(self, target_ids: list[str]) -> None:
        await self._post("/targets/remove", {"target_id_array": target_ids})

    async def set_targets_tag(self, target_ids: list[str], tag: str) -> None:
        await self._post("/targets/set/tag", {"id_array": target_ids, "tag": tag})

    # ── Tunnels ──────────────────────────────────────────────────────────

    async def list_tunnels_raw(self) -> list[dict]:
        data = await self._get("/tunnel/list")
        if isinstance(data, list):
            return data
        return []

    async def start_socks5(
        self, agent_id: str, lhost: str, lport: int,
        desc: str = "", listen: bool = True,
        use_auth: bool = False, username: str = "", password: str = ""
    ) -> str:
        """Start SOCKS5 tunnel. Returns tunnel_id."""
        result = await self._post("/tunnel/start/socks5", {
            "agent_id":  agent_id,
            "listen":    listen,
            "desc":      desc,
            "l_host":    lhost,
            "l_port":    lport,
            "use_auth":  use_auth,
            "username":  username,
            "password":  password,
        })
        return result.get("message", "")

    async def start_socks4(
        self, agent_id: str, lhost: str, lport: int,
        desc: str = "", listen: bool = True,
    ) -> str:
        result = await self._post("/tunnel/start/socks4", {
            "agent_id": agent_id,
            "listen":   listen,
            "desc":     desc,
            "l_host":   lhost,
            "l_port":   lport,
        })
        return result.get("message", "")

    async def start_lportfwd(
        self, agent_id: str, lhost: str, lport: int,
        thost: str, tport: int, desc: str = "", listen: bool = True,
    ) -> str:
        result = await self._post("/tunnel/start/lportfwd", {
            "agent_id": agent_id,
            "listen":   listen,
            "desc":     desc,
            "l_host":   lhost,
            "l_port":   lport,
            "t_host":   thost,
            "t_port":   tport,
        })
        return result.get("message", "")

    async def start_rportfwd(
        self, agent_id: str, port: int,
        thost: str, tport: int, desc: str = "", listen: bool = True,
    ) -> str:
        result = await self._post("/tunnel/start/rportfwd", {
            "agent_id": agent_id,
            "listen":   listen,
            "desc":     desc,
            "port":     port,
            "t_host":   thost,
            "t_port":   tport,
        })
        return result.get("message", "")

    async def stop_tunnel(self, tunnel_id: str) -> None:
        await self._post("/tunnel/stop", {"p_tunnel_id": tunnel_id})

    async def set_tunnel_info(self, tunnel_id: str, info: str) -> None:
        await self._post("/tunnel/set/info", {"p_tunnel_id": tunnel_id, "p_info": info})

    # ── Chat ─────────────────────────────────────────────────────────────

    async def send_chat(self, message: str) -> None:
        await self._post("/chat/send", {"message": message})

    # ── Services ─────────────────────────────────────────────────────────

    async def list_services_raw(self) -> list[dict]:
        data = await self._get("/service/list")
        services = data.get("services") if isinstance(data, dict) else data
        return services if isinstance(services, list) else []

    async def call_service(self, service: str, command: str, args: str = "") -> None:
        await self._post("/service/call", {
            "service": service,
            "command": command,
            "args":    args,
        })
