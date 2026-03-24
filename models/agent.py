from __future__ import annotations
from pydantic import BaseModel, Field


class Agent(BaseModel):
    """Represents a connected agent (beacon)."""

    # Core identity — all use a_ prefix as returned by the API
    id: str               = Field(..., alias="a_id")
    name: str             = Field(default="", alias="a_name")
    listener: str         = Field(default="", alias="a_listener")

    # Host information
    external_ip: str      = Field(default="", alias="a_external_ip")
    internal_ip: str      = Field(default="", alias="a_internal_ip")
    computer: str         = Field(default="", alias="a_computer")
    domain: str           = Field(default="", alias="a_domain")
    username: str         = Field(default="", alias="a_username")
    impersonated: str     = Field(default="", alias="a_impersonated")

    # Process / identity
    pid: str              = Field(default="", alias="a_pid")
    tid: str              = Field(default="", alias="a_tid")
    process: str          = Field(default="", alias="a_process")
    arch: str             = Field(default="", alias="a_arch")
    elevated: bool        = Field(default=False, alias="a_elevated")

    # OS
    os: int               = Field(default=0, alias="a_os")    # 1=Windows, 2=Linux, 3=macOS
    os_desc: str          = Field(default="", alias="a_os_desc")
    gmt_offset: int       = Field(default=0, alias="a_gmt_offset")

    # C2 timing
    async_: bool          = Field(default=False, alias="a_async")
    sleep: int            = Field(default=60, alias="a_sleep")
    jitter: int           = Field(default=0, alias="a_jitter")
    last_tick: int        = Field(default=0, alias="a_last_tick")

    # Metadata labels
    tags: str             = Field(default="", alias="a_tags")
    mark: str             = Field(default="", alias="a_mark")
    color: str            = Field(default="", alias="a_color")

    class Config:
        populate_by_name = True

    @property
    def os_name(self) -> str:
        mapping = {1: "Windows", 2: "Linux", 3: "macOS"}
        return mapping.get(self.os, "Unknown")

    def summary(self) -> str:
        """One-line textual summary for LLM consumption."""
        elevated_str = " [ELEVATED]" if self.elevated else ""
        return (
            f"[{self.id}] {self.computer}\\{self.username}{elevated_str} "
            f"| {self.os_name} {self.os_desc} | {self.process} (PID:{self.pid}) "
            f"| {self.internal_ip} / {self.external_ip} "
            f"| Listener: {self.listener} | Sleep: {self.sleep}s"
        )
