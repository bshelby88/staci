"""Credit Score Simulation API with Base USDC payment verification."""

from typing import Optional
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
import json, urllib.request, time, hashlib

BASE_RPC_URL = "https://mainnet.base.org"
TREASURY = "0x7861db4efc14a1ed5dd8c96c528a3796560f1393"
USDC_CONTRACT_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
USDC_DECIMALS = 6
TRANSFER_EVENT_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
KERNEL_URL = "https://rae-kernel.fly.dev/v1/events"

app = FastAPI(title="RAE Credit Score Simulation API", version="2.0.0", description="Production-ready with Base USDC payment verification.")

class CreditSimRequest(BaseModel):
    current_score: int = Field(..., ge=300, le=850)
    total_credit_limit: float = Field(..., ge=0)
    current_revolving_balance: float = Field(..., ge=0)
    derogatory_items_count: int = Field(0, ge=0)
    planned_paydown_amount: float = Field(0.0, ge=0)
    disputed_derogatories_count: int = Field(0, ge=0)

def _rpc_post(method: str, params: list) -> Optional[dict]:
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(BASE_RPC_URL, data=data, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result.get("result")
    except Exception as e:
        print(f"[PaymentVerification] RPC Error: {e}")
        return None

def _check_replay(tx_hash: str) -> bool:
    """Check AEK Kernel event store for existing dedup key (replay protection)."""
    dedup_key = f"base_revenue_{tx_hash[:16]}"
    try:
        url = f"{KERNEL_URL}?deduplication_key={dedup_key}"
        req = urllib.request.Request(url, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            events = json.loads(resp.read().decode('utf-8'))
            if isinstance(events, list):
                return len(events) > 0
            return False
    except Exception:
        return False

def _parse_usdc_transfer(log: dict) -> Optional[dict]:
    """Parse a USDC Transfer event log."""
    topics = log.get("topics", [])
    if len(topics) < 3:
        return None
    if topics[0].lower() != TRANSFER_EVENT_SIGNATURE.lower():
        return None
    to_address = "0x" + topics[2][-40:].lower()
    amount_hex = log.get("data", "0x")
    if not amount_hex or amount_hex == "0x":
        return None
    try:
        amount = int(amount_hex, 16) / (10 ** USDC_DECIMALS)
    except ValueError:
        return None
    return {"to": to_address, "amount": amount}

def verify_base_usdc_payment(tx_hash: Optional[str]) -> bool:
    if not tx_hash or not tx_hash.startswith("0x") or len(tx_hash) != 66:
        return False
    # Step 1: Query transaction by hash (chronicler pattern)
    tx_data = _rpc_post("eth_getTransactionByHash", [tx_hash])
    if not tx_data:
        return False
    # Step 2: Get receipt for status, confirmations, and logs
    receipt = _rpc_post("eth_getTransactionReceipt", [tx_hash])
    if not receipt:
        return False
    if receipt.get("status") != "0x1":
        return False
    # Step 3: Confirmation check (>=12 blocks)
    current_block = _rpc_post("eth_blockNumber", [])
    if current_block:
        current_block_num = int(current_block, 16)
        tx_block_num = int(receipt.get("blockNumber", "0x0"), 16)
        confirmations = current_block_num - tx_block_num
        if confirmations < 12:
            return False
    # Step 4: Check recipient
    to_address = receipt.get("to", "")
    if to_address.lower() != TREASURY.lower():
        return False
    # Step 5: Parse USDC transfer events
    usdc_transfer = None
    for log in receipt.get("logs", []):
        if log.get("address", "").lower() == USDC_CONTRACT_ADDRESS.lower():
            parsed = _parse_usdc_transfer(log)
            if parsed:
                usdc_transfer = parsed
    if not usdc_transfer:
        return False
    # Step 6: Replay protection — check dedup key against AEK Kernel event store
    if _check_replay(tx_hash):
        return False
    return True

def reject_unverified_payment_gate(): raise HTTPException(status_code=503, detail="Payment verification unavailable")

@app.get("/healthz")
def healthz(): return {"status": "operational", "payment_verification": "enabled"}

@app.post("/v1/credit/simulate")
def simulate_credit_score(req: CreditSimRequest, x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx")):
    if not x_402_payment_tx or not verify_base_usdc_payment(x_402_payment_tx): reject_unverified_payment_gate()
    utilization = (req.current_revolving_balance / req.total_credit_limit) * 100 if req.total_credit_limit > 0 else 0
    new_score = req.current_score - (utilization * 0.5) - (req.derogatory_items_count * 15) + (req.planned_paydown_amount / req.total_credit_limit * 20 if req.total_credit_limit > 0 else 0)
    return {"original_score": req.current_score, "projected_score": max(300, min(850, int(new_score))), "utilization_pct": round(utilization, 1)}
