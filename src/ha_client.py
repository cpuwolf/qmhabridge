from __future__ import annotations

import logging
from typing import Any, Dict

import requests


class HomeAssistantClient:
    """Minimal REST client for Home Assistant services."""

    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
        )

    def _post(self, path: str, json: Dict[str, Any] | None = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self.session.post(url, json=json, timeout=10)
        if response.status_code >= 400:
            logging.error("HA API error %s: %s", response.status_code, response.text)
            response.raise_for_status()
        return response

    def turn_on_light(self, entity_id: str) -> None:
        """Call light.turn_on service for given entity."""
        payload = {"entity_id": entity_id}
        self._post("/api/services/switch/turn_on", json=payload)


