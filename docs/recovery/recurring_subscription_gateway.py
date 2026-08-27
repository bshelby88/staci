"""
Recurring subscription gateway recovery artifact.
Paid activation is unavailable until verifiable settlement checks exist.
"""

from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

PAYMENT_DISABLED_DETAIL = (
    "Payment verification unavailable; paid fulfillment is disabled"
)
PAYMENT_DISABLED_RESPONSES = {
    503: {"description": PAYMENT_DISABLED_DETAIL},
}

app = FastAPI(
    title="RAE Recurring Subscription Gateway",
    version="1.0.0",
    description=(
        "Recovery artifact only. Payment verification is disabled and paid "
        "fulfillment is unavailable."
    ),
)


class SubscriptionRequest(BaseModel):
    subscriber_wallet: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")
    plan_tier: str = Field("PRO_UNLIMITED", pattern=r"^(PRO_UNLIMITED|ENTERPRISE)$")


class SubscriberStore:
    def __init__(self):
        self.active_subscriptions: Dict[str, Dict[str, Any]] = {}


store = SubscriberStore()


def verify_tx_hash(tx_hash: Optional[str]) -> bool:
    """Fail closed until chain, asset, recipient, amount, and replay checks exist."""
    return False


def reject_unverified_payment_gate() -> None:
    raise HTTPException(status_code=503, detail=PAYMENT_DISABLED_DETAIL)


@app.get("/healthz")
def healthz():
    return {
        "status": "degraded",
        "service": "RAE Recurring Subscription Gateway",
        "payment_verification": "disabled",
        "paid_fulfillment": "unavailable",
    }


@app.post(
    "/v1/subscription/subscribe",
    status_code=503,
    responses=PAYMENT_DISABLED_RESPONSES,
)
def subscribe(
    req: SubscriptionRequest,
    x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx"),
):
    reject_unverified_payment_gate()
