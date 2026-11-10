"""
agent/src/sender.py
HTTP sender: POSTs metric snapshots to the FastAPI backend.
Uses tenacity for retry with exponential back-off.
"""
from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class MetricSender:
    """
    Sends a collected metric snapshot to POST /api/v1/ingest.
    Automatically retries on network errors (up to 5 attempts).
    """

    def __init__(self, backend_url: str, api_key: str, timeout: int = 15) -> None:
        """
        Args:
            backend_url: Base URL of the FastAPI backend, e.g. "https://100.x.x.x"
            api_key: Raw API key issued for this agent.
            timeout: HTTP request timeout in seconds.
        """
        self.ingest_url = f"{backend_url.rstrip('/')}/api/v1/ingest"
        self._headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(self._headers)

    @retry(
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def send(self, payload: dict[str, Any]) -> bool:
        """
        POST the metric payload to the backend.

        Returns:
            True on HTTP 2xx.

        Raises:
            requests.HTTPError: on 4xx/5xx after retries exhausted.
            requests.ConnectionError / Timeout: if backend unreachable.
        """
        resp = self._session.post(
            self.ingest_url,
            json=payload,
            timeout=self._timeout,
            # Disable SSL verification for self-signed certs (dev only).
            # Set BACKEND_VERIFY_SSL=true in production with a trusted cert.
            verify=False,
        )
        if resp.status_code == 401:
            logger.error("API key rejected (401) — check AGENT_API_KEY in .env")
            return False
        if resp.status_code == 403:
            logger.error("Agent forbidden (403) — agent may be revoked")
            return False

        resp.raise_for_status()
        logger.debug("Metric sent OK | metric_id=%s", resp.json().get("metric_id"))
        return True
