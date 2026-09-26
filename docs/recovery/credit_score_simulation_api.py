"""Credit Score Simulation API with Base USDC payment verification."""

from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import json, urllib.request, time, hashlib

BASE_RPC_URL = "https://mainnet.base.org"
TREASURY = "0x9e6A95B5Bf1190B5aCD00508a8E9c72eDEd5fB60"

app = FastAPI(title="RAE Credit Score Simulation API", version="2.0.0", description="Production-ready with Base USDC payment verification.")

class CreditSimRequest(BaseModel):
    current_score: int = Field(..., ge=300, le=850)
    total_credit_limit: float = Field(..., ge=0)
    current_revolving_balance: float = Field(..., ge=0)
    derogatory_items_count: int = Field(0, ge=0)
    planned_paydown_amount: float = Field(0.0, ge=0)
    disputed_derogatories_count: int = Field(0, ge=0)

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

def reject_unverified_payment_gate(): raise HTTPException(status_code=503, detail="Payment verification unavailable")

@app.get("/healthz")
def healthz(): return {"status": "operational", "payment_verification": "enabled"}

@app.post("/v1/credit/simulate")
def simulate_credit_score(req: CreditSimRequest, x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx")):
    if not x_402_payment_tx or not verify_base_usdc_payment(x_402_payment_tx): reject_unverified_payment_gate()
    utilization = (req.current_revolving_balance / req.total_credit_limit) * 100 if req.total_credit_limit > 0 else 0
    new_score = req.current_score - (utilization * 0.5) - (req.derogatory_items_count * 15) + (req.planned_paydown_amount / req.total_credit_limit * 20 if req.total_credit_limit > 0 else 0)
    return {"original_score": req.current_score, "projected_score": max(300, min(850, int(new_score))), "utilization_pct": round(utilization, 1)}
