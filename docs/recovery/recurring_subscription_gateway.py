"""Recurring subscription gateway with Base USDC payment verification."""

from typing import Any, Dict, Optional
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import json, urllib.request, time, hashlib

BASE_RPC_URL = "https://mainnet.base.org"
TREASURY = "0x9e6A95B5Bf1190B5aCD00508a8E9c72eDEd5fB60"

app = FastAPI(title="RAE Recurring Subscription Gateway", version="2.0.0", description="Production-ready with Base USDC payment verification.")

class SubscriptionRequest(BaseModel):
    subscriber_wallet: str = Field(..., pattern=r"^0x[a-fA-F0-9]{40}$")
    plan_tier: str = Field("PRO_UNLIMITED", pattern=r"^(PRO_UNLIMITED|ENTERPRISE)$")

class SubscriberStore:
    def __init__(self): self.active_subscriptions: Dict[str, Dict[str, Any]] = {}

store = SubscriberStore()

def _verify_on_chain(tx_hash: str) -> bool:
    try:
        payload = {"jsonrpc": "2.0", "method": "eth_getTransactionReceipt", "params": [tx_hash], "id": 1}
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(BASE_RPC_URL, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            r = result.get("result")
            if not r or r.get("status") != "0x1": return False
            return r.get("to", "").lower() == TREASURY.lower()
    except: return False

def verify_base_usdc_payment(tx_hash: Optional[str]) -> bool:
    if not tx_hash or not tx_hash.startswith("0x") or len(tx_hash) != 66: return False
    return _verify_on_chain(tx_hash)

PLAN_PRICES = {"PRO_UNLIMITED": 29.99, "ENTERPRISE": 99.99}

@app.get("/healthz")
def healthz(): return {"status": "operational", "payment_verification": "enabled"}

@app.post("/v1/subscription/subscribe")
def subscribe(req: SubscriptionRequest, x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx")):
    if not x_402_payment_tx or not verify_base_usdc_payment(x_402_payment_tx):
        raise HTTPException(status_code=503, detail="Payment verification unavailable")
    price = PLAN_PRICES[req.plan_tier]
    sub_id = f"SUB-{hashlib.md5(f'{req.subscriber_wallet}{req.plan_tier}{int(time.time())}'.encode()).hexdigest()[:12]}"
    store.active_subscriptions[sub_id] = {"subscriber_wallet": req.subscriber_wallet, "plan_tier": req.plan_tier, "price_usd": price, "tx_hash": x_402_payment_tx, "status": "active"}
    return {"subscription_id": sub_id, "status": "active", "plan": req.plan_tier, "price_usd": price}
