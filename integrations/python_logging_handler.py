"""Python logging handler that forwards records to the incident platform."""

from __future__ import annotations

import logging
import threading

import httpx


class IncidentPlatformHandler(logging.Handler):
    """Forward Python log records to the platform's ``POST /logs`` endpoint.

    The handler resolves or creates the configured service once, then caches its
    numeric id. Network failures are intentionally swallowed so observability
    cannot break the application being observed.
    """

    def __init__(
        self,
        platform_url: str,
        service_name: str,
        *,
        timeout: float = 2.0,
        level: int = logging.NOTSET,
    ) -> None:
        super().__init__(level=level)
        self.platform_url = platform_url.rstrip("/")
        self.service_name = service_name
        self.timeout = timeout
        self._service_id: int | None = None
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            service_id = self._get_service_id()
            with httpx.Client(timeout=self.timeout, trust_env=False) as client:
                response = client.post(
                    f"{self.platform_url}/logs",
                    json={
                        "service_id": service_id,
                        "level": record.levelname,
                        "message": self.format(record),
                    },
                )
                response.raise_for_status()
        except Exception:
            self.handleError(record)

    def _get_service_id(self) -> int:
        if self._service_id is not None:
            return self._service_id

        with self._lock:
            if self._service_id is not None:
                return self._service_id

            with httpx.Client(timeout=self.timeout, trust_env=False) as client:
                services_response = client.get(f"{self.platform_url}/services")
                services_response.raise_for_status()
                for service in services_response.json():
                    if service["name"] == self.service_name:
                        self._service_id = service["id"]
                        return self._service_id

                create_response = client.post(
                    f"{self.platform_url}/services",
                    json={"name": self.service_name},
                )
                create_response.raise_for_status()
                self._service_id = create_response.json()["id"]
                return self._service_id

