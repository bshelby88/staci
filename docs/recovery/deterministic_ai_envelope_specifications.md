# Deterministic AI Envelope Specifications

**System Standard**: Protocol Specification for Guaranteed Execution Verification  
**Purpose**: Eliminate false-done task signals, fake revenue telemetry, inverted status heuristics, and silent failures across the RAE multi-agent fleet.

---

## 1. The Core Deterministic AI Envelope Principles

An **AI Envelope** is a programmatic wrapper around agent execution that intercepts task outputs and forces execution validation before state transitions are allowed.

```
   ┌─────────────────────────────────────────────────────────────┐
   │                       AGENT RUNTIME                         │
   │  ┌───────────────────────────────────────────────────────┐  │
   │  │ Prompt -> Inference -> Action (CLI / API Call)       │  │
   │  └──────────────────────────┬────────────────────────────┘  │
   └─────────────────────────────┼───────────────────────────────┘
                                 │ Raw Output / Claims
                                 ▼
   ┌─────────────────────────────────────────────────────────────┐
   │               DETERMINISTIC AI ENVELOPE                     │
   │  1. Check Process Exit Code == 0                            │
   │  2. Validate Output JSON against Schema (Pydantic/Zod)      │
   │  3. Verify Remote HTTP Status == 200 OK                     │
   │  4. Verify On-Chain RPC Tx Hash (for Revenue Events)        │
   └─────────────────────────────┬───────────────────────────────┘
                                 │
                     ┌───────────┴───────────┐
                     ▼                       ▼
              [PASSED VERIFICATION]    [FAILED VERIFICATION]
                     │                       │
                     ▼                       ▼
            Status: COMPLETED       Status: FAILED / RETRY
            Emit Telemetry Event    Quarantine Task & Alert
```

---

## 2. Specification Rules & Verification Contracts

### Rule 1: No ACK Without Execution (Exit Code Assertion)
* **Requirement**: No task runner (Staci, BEAN, Nimbus) may issue a completion ACK to Airtable or AEK Kernel unless the execution wrapper records an explicit exit code of `0`.
* **Execution Contract**:
  ```python
  class TaskExecutionReceipt(BaseModel):
      task_id: str
      agent_id: str
      command_executed: str
      exit_code: int
      stdout_summary: str
      stderr_summary: str
      execution_time_ms: int
      timestamp: datetime

      @validator("exit_code")
      def exit_code_must_be_zero(cls, v):
          if v != 0:
              raise ValueError("Task execution failed with non-zero exit code")
          return v
  ```

### Rule 2: Strict Isolation of Revenue Telemetry (Base Chain Verification)
* **Requirement**: The event type `revenue.sale` is strictly prohibited from being emitted by mock generators, sandbox test suites, or dry-run scripts.
* **Verification Rule**: Every `revenue.sale` event MUST include a validated Base RPC transaction hash or Stripe payment intent ID verified against live APIs.
* **Telemetry Verification Schema**:
  ```python
  class RevenueSaleEvent(BaseModel):
      event_id: str
      amount_usd: float
      currency: str  # Must be 'USDC' or 'USD'
      source: str    # 'Base_Mainnet' or 'Stripe_Live'
      tx_hash_or_intent: str
      verified_on_chain: bool

      @validator("verified_on_chain")
      def verify_on_chain_flag(cls, v, values):
          if not v:
              raise ValueError("Unverified revenue telemetry cannot be emitted onto production bus")
          return v
  ```

### Rule 3: Anti-Truncation Social Publisher Validation
* **Requirement**: Social media publishing tools (Tiffany / Blotato) must validate character lengths against platform boundaries *before* dispatch and parse returned platform IDs *after* dispatch.
* **Platform Constraints**:
  - Twitter / X standard post: Max 280 characters.
  - Telegram broadcast: Max 4096 characters.
  - HeyGen video script: Max 1500 words per render call.

### Rule 4: Health Check Response Contract
* **Requirement**: All microservices (`tradingagents-x402`, `sentry-forge-x402`, `staci-core`) must expose a standardized `/healthz` endpoint returning JSON metadata:
  ```json
  {
    "service": "staci-core",
    "status": "ok",
    "uptime_seconds": 86400,
    "version": "v0.4.1",
    "git_commit": "100b65f",
    "checks": {
      "airtable_bus": "connected",
      "postgres_queue": "connected",
      "fly_api": "authenticated"
    }
  }
  ```

---

## 3. Implementation Blueprint for Agent Task Runners

Below is the Python wrapper to be integrated into all agent runners to enforce the Deterministic Envelope:

```python
# rae_aek/envelope.py
import subprocess
import time
from typing import Callable, Any

def execute_with_envelope(task_id: str, command: list[str], verifier: Callable[[str], bool] = None) -> dict:
    start_time = time.time()
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        duration = int((time.time() - start_time) * 1000)
        
        # 1. Exit Code Verification
        if result.returncode != 0:
            return {
                "status": "FAILED",
                "reason": f"Non-zero exit code {result.returncode}",
                "stderr": result.stderr[:500]
            }
        
        # 2. Optional Artifact Verifier
        if verifier and not verifier(result.stdout):
            return {
                "status": "FAILED",
                "reason": "Custom verification heuristic failed on stdout",
                "stdout": result.stdout[:500]
            }
            
        return {
            "status": "COMPLETED",
            "exit_code": 0,
            "stdout": result.stdout[:500],
            "duration_ms": duration
        }
    except Exception as e:
        return {
            "status": "FAILED",
            "reason": f"Execution exception: {str(e)}"
        }
```
