"""Shared fixtures for the POMatch_Reference test suite."""

from __future__ import annotations

import os

import httpx
import pytest

import main


@pytest.fixture(autouse=True)
def isolate_erp_url(monkeypatch: pytest.MonkeyPatch):
    """ERP_PO_LOOKUP_URL (the complete URL) beats ERP_API_URL; clear it so a value exported in the
    shell cannot redirect the suite. Tests that exercise it set it explicitly."""
    monkeypatch.delenv("ERP_PO_LOOKUP_URL", raising=False)


@pytest.fixture
def erp_url() -> str:
    return os.getenv("ERP_API_URL", main.DEFAULT_ERP_API_URL).rstrip("/")


@pytest.fixture
def live_erp(erp_url: str) -> str:
    """Base URL of a reachable mock ERP. Fails loudly (does not skip) when it is not running,
    because the point of the live tests is to prove the function against the real contract.
    Set POMATCH_SKIP_LIVE=1 to skip instead."""
    if os.getenv("POMATCH_SKIP_LIVE") == "1":
        pytest.skip("POMATCH_SKIP_LIVE=1")
    try:
        response = httpx.get(f"{erp_url}/health", timeout=5)
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 - we want the reason in the message
        pytest.fail(
            f"mock ERP not reachable at {erp_url} ({exc}). Start it with "
            "`node server.mjs` in commercial_bootcamp_lab_assets/mock-erp, or set ERP_API_URL."
        )
    assert payload == {"ok": True, "service": "erp-po-api"}, payload
    return erp_url


@pytest.fixture
def mock_erp(monkeypatch: pytest.MonkeyPatch):
    """Route po_lookup's HTTP call through an httpx.MockTransport driven by a handler.

    Usage: ``mock_erp(lambda request: httpx.Response(200, json={...}))``.
    The handler may also raise an httpx exception to simulate network failures.
    """

    def install(handler):
        monkeypatch.setattr(main, "_erp_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
        return handler

    return install
