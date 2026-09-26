"""RAE monetization gateway with Base USDC payment verification."""

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import uvicorn
import json
import urllib.request
import time
import hashlib
from typing import Optional

app = FastAPI(
    title="RAE Monetization & Machine Commerce Gateway",
    version="2.0.0",
    description="Production-ready Base USDC payment verification with x402 integration."
)

PAYMENT_DISABLED_DETAIL = "Payment verification unavailable; paid fulfillment is disabled"
PAYMENT_DISABLED_RESPONSES = {503: {"description": PAYMENT_DISABLED_DETAIL}}

BASE_RPC_URL = "https://mainnet.base.org"
USDC_CONTRACT_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
TREASURY_WALLET = "0x9e6A95B5Bf1190B5aCD00508a8E9c72eDEd5fB60"
USDC_DECIMALS = 6

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

class PaymentVerification:
    @staticmethod
    def _rpc_post(method: str, params: list) -> Optional[dict]:
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        data = json.dumps(payload).encode('utf-8')
        headers = {'Content-Type': 'application/json', 'User-Agent': 'RAE-Monetization/2.0'}
        try:
            req = urllib.request.Request(BASE_RPC_URL, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result.get("result")
        except Exception as e:
            print(f"[PaymentVerification] RPC Error: {e}")
            return None

    @staticmethod
    def verify_base_usdc_payment(tx_hash: Optional[str], required_amount: float) -> dict:
        if not tx_hash or not tx_hash.startswith("0x") or len(tx_hash) != 66:
            return {"verified": False, "reason": "Invalid tx_hash format", "details": {}}
        receipt = PaymentVerification._rpc_post("eth_getTransactionReceipt", [tx_hash])
        if not receipt:
            return {"verified": False, "reason": "Transaction not found on Base mainnet", "details": {"tx_hash": tx_hash}}
        if receipt.get("status") != "0x1":
            return {"verified": False, "reason": "Transaction failed on-chain", "details": {"tx_hash": tx_hash, "status": receipt.get("status")}}
        current_block = PaymentVerification._rpc_post("eth_blockNumber", [])
        confirmations = 0
        if current_block:
            current_block_num = int(current_block, 16)
            tx_block_num = int(receipt.get("blockNumber", "0x0"), 16)
            confirmations = current_block_num - tx_block_num
            if confirmations < 12:
                return {"verified": False, "reason": f"Insufficient confirmations: {confirmations}/12", "details": {"tx_hash": tx_hash, "confirmations": confirmations}}
        logs = receipt.get("logs", [])
        usdc_transfer_found = False
        transfer_amount = 0
        for log in logs:
            if log.get("address", "").lower() == USDC_CONTRACT_ADDRESS.lower():
                if len(log.get("topics", [])) >= 3:
                    try:
                        amount_hex = log["data"]
                        if amount_hex and amount_hex != "0x":
                            transfer_amount = int(amount_hex, 16) / (10 ** USDC_DECIMALS)
                            usdc_transfer_found = True
                    except (ValueError, KeyError):
                        pass
        if not usdc_transfer_found:
            return {"verified": False, "reason": "No USDC transfer found in transaction logs", "details": {"tx_hash": tx_hash}}
        tolerance = required_amount * 0.01
        if abs(transfer_amount - required_amount) > tolerance:
            return {"verified": False, "reason": f"Amount mismatch", "details": {"expected": required_amount, "actual": transfer_amount}}
        to_address = receipt.get("to", "")
        if to_address.lower() != TREASURY_WALLET.lower():
            return {"verified": False, "reason": "Recipient mismatch", "details": {"recipient": to_address}}
        return {"verified": True, "reason": "Payment verified on Base mainnet", "details": {"tx_hash": tx_hash, "amount_usdc": transfer_amount, "confirmations": confirmations, "recipient": TREASURY_WALLET}}

def reject_unverified_payment_gate() -> None:
    raise HTTPException(status_code=503, detail=PAYMENT_DISABLED_DETAIL)

@app.get("/healthz")
def healthz():
    return {"status": "operational", "payment_verification": "enabled", "paid_fulfillment": "available"}

@app.get("/v1/products")
def list_products():
    return {"shelf_products": [
        {"id": "prod_dispute_forge", "name": "Dispute Forge Credit Defense Package", "payment_status": "enabled", "x402_price_usd": 49.00},
        {"id": "prod_bean_course", "name": "Build Your Own BEAN 16-Agent Masterclass", "payment_status": "enabled", "x402_price_usd": 197.00},
        {"id": "prod_sentry_forge_api", "name": "Sentry Forge Legal Intake Analysis x402", "payment_status": "enabled", "x402_price_usd": 5.00}
    ]}

@app.post("/v1/dispute/generate", responses={402: {"description": "Payment required"}, 503: {"description": PAYMENT_DISABLED_DETAIL}})
def generate_dispute_letter(req: DisputeRequest, x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx")):
    if not x_402_payment_tx: reject_unverified_payment_gate()
    v = PaymentVerification.verify_base_usdc_payment(x_402_payment_tx, 49.00)
    if not v["verified"]: raise HTTPException(status_code=402, detail=json.dumps(v))
    return {"status": "success", "dispute_id": f"DISP-{int(time.time())}", "payment_verified": True}

@app.post("/v1/sentry/analyze-case", responses={402: {"description": "Payment required"}, 503: {"description": PAYMENT_DISABLED_DETAIL}})
def analyze_case(req: SentryCaseRequest, x_402_payment_tx: Optional[str] = Header(None, alias="X-402-Payment-Tx")):
    if not x_402_payment_tx: reject_unverified_payment_gate()
    v = PaymentVerification.verify_base_usdc_payment(x_402_payment_tx, 5.00)
    if not v["verified"]: raise HTTPException(status_code=402, detail=json.dumps(v))
    return {"status": "success", "case_id": f"SENT-{int(time.time())}", "payment_verified": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
