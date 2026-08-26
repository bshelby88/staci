"""
RAE Monetization Microservice Engine
Powers Dispute Forge ($49 direct / $5 x402 API) and Sentry Forge ($5/case API).
"""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn
from typing import Optional

app = FastAPI(
    title="RAE Monetization & Machine Commerce Gateway",
    version="1.0.0",
    description="Paid fulfillment is disabled until Base USDC payment verification is implemented."
)

BASE_WALLET = "0x9e6A95B5Bf1190B5aCD00508a8E9c72eDEd5fB60"
PAYMENT_DISABLED_DETAIL = "Payment verification unavailable; paid fulfillment is disabled"

class DisputeRequest(BaseModel):
    client_name: str
    creditor_name: str
    account_number_last4: str
    dispute_reason: str
    fdcpa_violation_claimed: Optional[str] = "FDCPA 15 U.S.C. 1692g"

class SentryCaseRequest(BaseModel):
    case_summary: str
    jurisdiction: str = "Federal Court"
    claimed_damages_usd: float

def verify_base_usdc_payment(tx_hash: Optional[str], required_amount: float) -> bool:
    """Fail closed until chain, transfer, confirmation, and replay checks exist."""
    return False

def reject_unverified_payment_gate() -> None:
    raise HTTPException(status_code=503, detail=PAYMENT_DISABLED_DETAIL)

@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "wallet": BASE_WALLET,
        "payment_verification": "disabled",
        "active_products": ["Dispute Forge ($49)", "Sentry Forge ($5)", "BEAN Course ($197)"]
    }

@app.get("/v1/products")
def list_products():
    return {
        "shelf_products": [
            {
                "id": "prod_dispute_forge",
                "name": "Dispute Forge Credit Defense Package",
                "human_price_usd": 49.00,
                "payment_status": "disabled",
                "checkout_url": "https://gumroad.com/l/dispute-forge-49"
            },
            {
                "id": "prod_bean_course",
                "name": "Build Your Own BEAN 16-Agent Masterclass",
                "human_price_usd": 197.00,
                "checkout_url": "https://gumroad.com/l/build-your-own-bean-197"
            },
            {
                "id": "prod_sentry_forge_api",
                "name": "Sentry Forge Legal Intake Analysis x402",
                "payment_status": "disabled",
                "endpoint": "POST /v1/sentry/analyze-case"
            }
        ]
    }

@app.post("/v1/dispute/generate")
def generate_dispute_letter(req: DisputeRequest, x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx")):
    reject_unverified_payment_gate()

@app.post("/v1/sentry/analyze-case")
def analyze_case(req: SentryCaseRequest, x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx")):
    reject_unverified_payment_gate()

if __name__ == "__main__":
    print("Launching RAE Monetization Microservice on port 8090...")
    uvicorn.run(app, host="0.0.0.0", port=8090)
