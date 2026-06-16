from __future__ import annotations

import logging
import os
import time

from fastapi import FastAPI, HTTPException

from integrations.python_logging_handler import IncidentPlatformHandler


app = FastAPI(title="Demo Payment Service")
fault_mode = "none"

logger = logging.getLogger("demo-payment-service")
logger.setLevel(logging.INFO)
logger.handlers.clear()
handler = IncidentPlatformHandler(
    platform_url=os.getenv("INCIDENT_API_URL", "http://127.0.0.1:8000"),
    service_name=os.getenv("SERVICE_NAME", "demo-payment-service"),
    timeout=10.0,
)
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "fault_mode": fault_mode}


@app.post("/faults/{mode}")
def set_fault(mode: str) -> dict[str, str]:
    global fault_mode
    if mode not in {"none", "database", "timeout", "auth"}:
        raise HTTPException(status_code=400, detail="mode must be none, database, timeout, or auth")
    fault_mode = mode
    return {"fault_mode": fault_mode}


@app.post("/payments")
def create_payment() -> dict[str, str]:
    logger.info("Payment request received")
    if fault_mode == "database":
        logger.error("DBConnectionTimeout while connecting to mysql-primary")
        logger.error("Payment request failed after database retry")
        logger.error("Payment API returned 500 because database connection failed")
        raise HTTPException(status_code=500, detail="database unavailable")
    if fault_mode == "timeout":
        time.sleep(1)
        logger.error("Upstream payment request timed out after 30 seconds")
        logger.error("Payment provider timeout retry exhausted")
        logger.error("Payment API returned 504 after upstream timeout")
        raise HTTPException(status_code=504, detail="upstream timeout")
    if fault_mode == "auth":
        logger.error("Unauthorized payment token rejected")
        logger.error("Authentication failed for payment request")
        logger.error("Invalid API key blocked payment provider request")
        raise HTTPException(status_code=401, detail="authentication failed")
    logger.info("Payment completed successfully")
    return {"status": "paid"}
