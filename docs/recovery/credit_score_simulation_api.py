"""
Credit Score Simulation API recovery artifact.
Paid fulfillment is unavailable until verifiable settlement checks exist.
"""

from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

PAYMENT_DISABLED_DETAIL = (
    "Payment verification unavailable; paid fulfillment is disabled"
)
PAYMENT_DISABLED_RESPONSES = {
    503: {"description": PAYMENT_DISABLED_DETAIL},
}

app = FastAPI(
    title="RAE Credit Score Simulation API",
    version="1.0.0",
    description=(
        "Recovery artifact only. Payment verification is disabled and paid "
        "fulfillment is unavailable."
    ),
)


class CreditSimRequest(BaseModel):
    current_score: int = Field(..., ge=300, le=850)
    total_credit_limit: float = Field(..., ge=0)
    current_revolving_balance: float = Field(..., ge=0)
    derogatory_items_count: int = Field(0, ge=0)
    planned_paydown_amount: float = Field(0.0, ge=0)
    disputed_derogatories_count: int = Field(0, ge=0)


def verify_base_usdc_payment(tx_hash: Optional[str]) -> bool:
    """Fail closed until chain, asset, recipient, amount, and replay checks exist."""
    return False


def reject_unverified_payment_gate() -> None:
    raise HTTPException(status_code=503, detail=PAYMENT_DISABLED_DETAIL)


@app.get("/healthz")
def healthz():
    return {
        "status": "degraded",
        "service": "Credit Score Simulation API",
        "payment_verification": "disabled",
        "paid_fulfillment": "unavailable",
    }


@app.post(
    "/v1/credit/simulate",
    status_code=503,
    responses=PAYMENT_DISABLED_RESPONSES,
)
def simulate_credit_score(
    req: CreditSimRequest,
    x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx"),
):
    reject_unverified_payment_gate()
