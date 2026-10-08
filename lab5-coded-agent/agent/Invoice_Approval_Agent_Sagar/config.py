"""Runtime configuration, read from environment variables.

No credentials live here: the UiPath Python SDK uses the session that
`uip login` established (the `uip codedagent` wrapper injects it locally; the
robot injects it when deployed).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

AGENT_NAME = "Invoice_Approval_Agent_Sagar"
PACKAGE_VERSION = "1.0"

DEFAULT_ENTITY_NAME = "AP_Invoice_Sagar"
DEFAULT_LLM_MODEL = "gpt-4o-2024-11-20"

ENV_ENTITY_NAME = "AP_INVOICE_ENTITY_NAME"
ENV_ENTITY_ID = "AP_INVOICE_ENTITY_ID"  # set to skip the retrieve_by_name lookup
ENV_LLM_MODEL = "AP_INVOICE_LLM_MODEL"


@dataclass(frozen=True)
class Settings:
    entity_name: str
    entity_id: str | None
    llm_model: str


def load_settings() -> Settings:
    return Settings(
        entity_name=(os.getenv(ENV_ENTITY_NAME) or DEFAULT_ENTITY_NAME).strip(),
        entity_id=(os.getenv(ENV_ENTITY_ID) or "").strip() or None,
        llm_model=(os.getenv(ENV_LLM_MODEL) or DEFAULT_LLM_MODEL).strip(),
    )
