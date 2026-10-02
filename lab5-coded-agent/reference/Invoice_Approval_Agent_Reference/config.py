"""Runtime configuration for the reference agent.

Everything here is read from environment variables so the same code runs
locally (``uip codedagent run``), in evaluations, and after deployment to
``APAutomation_<user_name>``. Copy ``.env.example`` to ``.env`` and fill in the
placeholders. No credentials live here: the UiPath Python SDK picks up the
session that ``uip login`` established (the ``uip codedagent`` wrapper injects
``UIPATH_URL`` / ``UIPATH_ACCESS_TOKEN``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Placeholder that participants replace with their signed-in first name.
# The canonical entity name from commercial-process.md is AP_Invoice_<user_name>;
# the reference solution uses the _Reference suffix so it never collides with a
# participant's entity.
DEFAULT_ENTITY_NAME = "AP_Invoice_Reference"
DEFAULT_LLM_MODEL = "gpt-4o-2024-11-20"
AGENT_NAME = "Invoice_Approval_Agent_Reference"
PACKAGE_VERSION = "1.0"

ENV_ENTITY_NAME = "AP_INVOICE_ENTITY_NAME"
ENV_ENTITY_ID = "AP_INVOICE_ENTITY_ID"
ENV_LLM_MODEL = "AP_INVOICE_LLM_MODEL"
ENV_NARRATIVE_MODE = "AP_INVOICE_NARRATIVE_MODE"
ENV_FIXTURE_FILE = "AP_INVOICE_FIXTURE_FILE"
ENV_FIXTURE_OUTPUT_DIR = "AP_INVOICE_FIXTURE_OUTPUT_DIR"

NARRATIVE_MODE_LLM = "llm"
NARRATIVE_MODE_TEMPLATE = "template"


@dataclass(frozen=True)
class Settings:
    entity_name: str
    entity_id: str | None
    llm_model: str
    narrative_mode: str
    fixture_file: str | None
    fixture_output_dir: str

    @property
    def offline(self) -> bool:
        """True when Data Fabric is replaced by a local CSV/JSON fixture."""
        return bool(self.fixture_file)


def load_settings(entity_name_override: str | None = None) -> Settings:
    """Build Settings from the environment (with an optional per-run entity override)."""
    entity_name = (entity_name_override or os.getenv(ENV_ENTITY_NAME) or DEFAULT_ENTITY_NAME).strip()
    narrative_mode = os.getenv(ENV_NARRATIVE_MODE, NARRATIVE_MODE_LLM).strip().lower()
    if narrative_mode not in (NARRATIVE_MODE_LLM, NARRATIVE_MODE_TEMPLATE):
        raise ValueError(
            f"{ENV_NARRATIVE_MODE} must be '{NARRATIVE_MODE_LLM}' or '{NARRATIVE_MODE_TEMPLATE}', got {narrative_mode!r}"
        )
    return Settings(
        entity_name=entity_name,
        entity_id=(os.getenv(ENV_ENTITY_ID) or None),
        llm_model=os.getenv(ENV_LLM_MODEL, DEFAULT_LLM_MODEL),
        narrative_mode=narrative_mode,
        fixture_file=(os.getenv(ENV_FIXTURE_FILE) or None),
        fixture_output_dir=os.getenv(ENV_FIXTURE_OUTPUT_DIR, "fixture-output"),
    )
