from __future__ import annotations
from pydantic import BaseModel, Field


# Message type constants (match Go constants ts_syncpacket.go CONSOLE_OUT_*)
MSG_TYPE_EMPTY    = 0
MSG_TYPE_GOOD     = 7   # CONSOLE_OUT_SUCCESS
MSG_TYPE_INFO     = 5   # CONSOLE_OUT_INFO
MSG_TYPE_WARNING  = 6   # CONSOLE_OUT_ERROR (approximate)
MSG_TYPE_ERROR    = 6   # CONSOLE_OUT_ERROR
MSG_TYPE_CONSOLE  = 10  # CONSOLE_OUT


class Task(BaseModel):
    """Represents a completed task in the AdaptixC2 task history.
    
    Field aliases match the actual API response JSON (a_* prefix),
    confirmed by live test against /agent/task/list endpoint.
    """

    task_id: str      = Field(default="", alias="a_task_id")
    agent_id: str     = Field(default="", alias="a_id")
    client: str       = Field(default="", alias="a_client")
    hook_id: str      = Field(default="", alias="a_hook_id")
    command_line: str = Field(default="", alias="a_cmdline")
    message_type: int = Field(default=0,  alias="a_msg_type")
    message: str      = Field(default="", alias="a_message")
    clear_text: str   = Field(default="", alias="a_text")
    completed: bool   = Field(default=False, alias="a_completed")
    start_time: int   = Field(default=0, alias="a_start_time")
    finish_time: int  = Field(default=0, alias="a_finish_time")

    class Config:
        populate_by_name = True

    @property
    def is_error(self) -> bool:
        """True when the task completed with an error."""
        return self.message_type == MSG_TYPE_ERROR

    @property
    def output(self) -> str:
        """
        Return the plaintext output for the LLM.
        Prefer clear_text when available (formatted output),
        fall back to message.
        """
        return self.clear_text if self.clear_text else self.message
