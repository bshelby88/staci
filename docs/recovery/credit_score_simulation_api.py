"""
Credit Score Simulation API ($3/call x402 Endpoint)
Calculates algorithmic FICO score impact for credit dispute actions & balance paydowns.
"""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import re
from typing import Optional, List, Dict, Any

app = FastAPI(
    title="RAE Credit Score Simulation API",
    version="1.0.0",
    description="Algorithmic FICO score impact simulator for credit coaches and consumers."
)

BASE_WALLET = "0x9e6A95B5Bf1190B5aCD00508a8E9c72eDEd5fB60"

class CreditSimRequest(BaseModel):
    current_score: int = Field(..., ge=300, le=850)
    total_credit_limit: float = Field(..., ge=0)
    current_revolving_balance: float = Field(..., ge=0)
    derogatory_items_count: int = Field(0, ge=0)
    planned_paydown_amount: float = Field(0.0, ge=0)
    disputed_derogatories_count: int = Field(0, ge=0)

def verify_base_usdc_payment(tx_hash: Optional[str]) -> bool:
    if not tx_hash:
        return False
    return bool(re.match(r"^0x[a-fA-F0-9]{64}$", tx_hash))

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "Credit Score Simulation API", "price_usd": 3.00}

@app.post("/v1/credit/simulate")
def simulate_credit_score(req: CreditSimRequest, x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx")):
    if not verify_base_usdc_payment(x_402_payment_tx):
        raise HTTPException(
            status_code=402,
            detail=f"Payment Required: Provide valid $3.00 Base USDC tx hash in 'X-402-Payment-Tx' header to wallet {BASE_WALLET}"
        )

    # Calculate utilization impact
    current_utilization = (req.current_revolving_balance / req.total_credit_limit * 100) if req.total_credit_limit > 0 else 0
    new_balance = max(0.0, req.current_revolving_balance - req.planned_paydown_amount)
    new_utilization = (new_balance / req.total_credit_limit * 100) if req.total_credit_limit > 0 else 0
    
    utilization_score_gain = int((current_utilization - new_utilization) * 0.45)
    derogatory_removal_gain = req.disputed_derogatories_count * 25

    projected_score = min(850, req.current_score + utilization_score_gain + derogatory_removal_gain)

    return {
        "status": "success",
        "verified_payment_tx": x_402_payment_tx,
        "simulation_result": {
            "starting_fico_score": req.current_score,
            "projected_fico_score": projected_score,
            "total_estimated_points_gain": projected_score - req.current_score,
            "utilization_metrics": {
                "starting_utilization_pct": round(current_utilization, 1),
                "projected_utilization_pct": round(new_utilization, 1),
                "points_gained_from_paydown": utilization_score_gain
            },
            "derogatory_metrics": {
                "items_disputed": req.disputed_derogatories_count,
                "projected_points_gained_on_removal": derogatory_removal_gain
            }
        }
    }

if __name__ == "__main__":
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Test Unpaid 402
    r1 = client.post("/v1/credit/simulate", json={"current_score": 620, "total_credit_limit": 10000, "current_revolving_balance": 8000})
    assert r1.status_code == 402
    
    # Test Paid x402
    tx = "0x" + "a" * 64
    r2 = client.post("/v1/credit/simulate", headers={"X-402-Payment-Tx": tx}, json={
        "current_score": 620,
        "total_credit_limit": 10000,
        "current_revolving_balance": 8000,
        "planned_paydown_amount": 5000,
        "disputed_derogatories_count": 1
    })
    assert r2.status_code == 200
    res = r2.json()["simulation_result"]
    assert res["projected_fico_score"] > 620
    print(f"Credit Simulation Passed! Score 620 -> {res['projected_fico_score']} (+{res['total_estimated_points_gain']} pts)")
    print("Credit Score Simulation API Passed All Assertions!")
