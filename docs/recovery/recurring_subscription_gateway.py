"""
RAE $99/mo SaaS Recurring Subscription Gateway
Provides unlimited x402 API access across 14 Fly.io microservices via monthly Base USDC subscriptions.
"""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import time
import re
from typing import Optional, Dict, Any

app = FastAPI(
    title="RAE $99/mo Recurring SaaS Subscription Gateway",
    version="1.0.0",
    description="Recurring monthly subscription API for unlimited x402 fleet endpoints."
)

BASE_WALLET = "0x9e6A95B5Bf1190B5aCD00508a8E9c72eDEd5fB60"
MONTHLY_PRICE_USDC = 99.00

class SubscriptionRequest(BaseModel):
    subscriber_wallet: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")
    plan_tier: str = Field("PRO_UNLIMITED", pattern=r"^(PRO_UNLIMITED|ENTERPRISE)$")

class SubscriberStore:
    def __init__(self):
        self.active_subscriptions: Dict[str, Dict[str, Any]] = {}

    def activate_subscription(self, wallet: str, tx_hash: str) -> Dict[str, Any]:
        now = int(time.time())
        expires_at = now + (30 * 86400) # 30 days
        sub_info = {
            "wallet": wallet,
            "status": "ACTIVE",
            "plan_tier": "PRO_UNLIMITED",
            "activated_at": now,
            "expires_at": expires_at,
            "payment_tx": tx_hash,
            "unlimited_api_access": True
        }
        self.active_subscriptions[wallet.lower()] = sub_info
        return sub_info

store = SubscriberStore()

def verify_tx_hash(tx_hash: Optional[str]) -> bool:
    return bool(tx_hash and re.match(r"^0x[a-fA-F0-9]{64}$", tx_hash))

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "RAE $99/mo SaaS Subscription Gateway", "price_monthly_usdc": MONTHLY_PRICE_USDC}

@app.post("/v1/subscription/subscribe")
def subscribe(req: SubscriptionRequest, x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx")):
    if not verify_tx_hash(x_402_payment_tx):
        raise HTTPException(
            status_code=402,
            detail=f"Payment Required: Send $99.00 Base USDC to {BASE_WALLET} and pass tx hash in 'X-402-Payment-Tx' header."
        )

    sub_info = store.activate_subscription(req.subscriber_wallet, x_402_payment_tx)
    return {
        "status": "success",
        "message": f"Successfully activated 30-day PRO_UNLIMITED subscription for wallet {req.subscriber_wallet}",
        "subscription": sub_info
    }

if __name__ == "__main__":
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # Test 402 Unpaid
    r1 = client.post("/v1/subscription/subscribe", json={"subscriber_wallet": "0x1111111111111111111111111111111111111111"})
    assert r1.status_code == 402

    # Test 200 Paid
    tx = "0x" + "b" * 64
    r2 = client.post("/v1/subscription/subscribe", headers={"X-402-Payment-Tx": tx}, json={"subscriber_wallet": "0x1111111111111111111111111111111111111111"})
    assert r2.status_code == 200
    res = r2.json()["subscription"]
    assert res["status"] == "ACTIVE"
    assert res["unlimited_api_access"] is True
    print(f"SaaS Subscription Activated! Wallet {res['wallet']} active until timestamp {res['expires_at']}")
    print("SaaS Subscription Gateway Passed All Assertions!")
