"""
AdaptixC2 MCP Server — Configuration
Loads settings from environment variables or .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the package directory
_env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_env_path)


class Config:
    # ── TeamServer connection ──────────────────────────────────────────────
    HOST: str = os.getenv("ADAPTIX_HOST", "127.0.0.1")
    PORT: int = int(os.getenv("ADAPTIX_PORT", "443"))
    ENDPOINT: str = os.getenv("ADAPTIX_ENDPOINT", "/endpoint")   # e.g. "" or "/api"
    USE_TLS: bool = os.getenv("ADAPTIX_USE_TLS", "true").lower() == "true"
    VERIFY_SSL: bool = os.getenv("ADAPTIX_VERIFY_SSL", "false").lower() == "true"

    # ── Credentials ───────────────────────────────────────────────────────
    USERNAME: str = os.getenv("ADAPTIX_USERNAME", "admin")
    PASSWORD: str = os.getenv("ADAPTIX_PASSWORD", "changeme")

    # ── Derived URLs ──────────────────────────────────────────────────────
    @classmethod
    def base_url(cls) -> str:
        scheme = "https" if cls.USE_TLS else "http"
        return f"{scheme}://{cls.HOST}:{cls.PORT}{cls.ENDPOINT}"

    @classmethod
    def ws_url(cls) -> str:
        scheme = "wss" if cls.USE_TLS else "ws"
        return f"{scheme}://{cls.HOST}:{cls.PORT}{cls.ENDPOINT}"

    # ── Timing ────────────────────────────────────────────────────────────
    # How long to poll for a task result (seconds)
    TASK_POLL_TIMEOUT: int = int(os.getenv("ADAPTIX_TASK_TIMEOUT", "120"))
    TASK_POLL_INTERVAL: float = float(os.getenv("ADAPTIX_POLL_INTERVAL", "2.0"))

    # Access token refresh margin (seconds before expiry)
    TOKEN_REFRESH_MARGIN: int = int(os.getenv("ADAPTIX_TOKEN_REFRESH_MARGIN", "60"))

    # ── MCP Server ────────────────────────────────────────────────────────
    MCP_SERVER_NAME: str = os.getenv("MCP_SERVER_NAME", "AdaptixC2")
    MCP_LOG_LEVEL: str = os.getenv("MCP_LOG_LEVEL", "INFO")
