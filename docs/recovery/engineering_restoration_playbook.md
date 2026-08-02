# RAE 100% Engineering Restoration Playbook

**Target Systems**: `bshelby88/nimbus-agent`, `rae-aek-v0.4`, `staci-core`, `bean-agent`, `tradingagents-x402`, Fly.io Apps, GitHub Actions  
**Purpose**: Step-by-step technical execution manual for software engineers and autonomous agents to restore RAE codebase, infrastructure, and revenue services.

---

## Module 1: Unpushed Commit & Git Repository Restoration

### Problem Statement
Commit `100b65f` in `repos/nimbus-agent` added a health server and `fly.toml` `/health` check mapping, but was never pushed to GitHub or deployed to Fly.io.

### Engineering Action Steps
1. Navigate to local repo directory:
   ```bash
   cd C:\Users\jaded\OneDrive\multiAgentic\repos\nimbus-agent
   ```
2. Verify local git log and unpushed status:
   ```bash
   git status
   git log -n 5 --oneline
   ```
3. Push unpushed commits to remote GitHub repository:
   ```bash
   git pull --rebase origin main
   git push origin main
   ```
4. Trigger Fly.io deployment with verified org token:
   ```bash
   flyctl deploy --app nimbus-agent --remote-only
   ```
5. Confirm HTTP 200 health response:
   ```bash
   curl -i https://nimbus-agent.fly.dev/health
   ```

---

## Module 2: Credential Scrubbing & Token Scope Remediation

### Remediation of BLK-1 (Personal Fly Token Scope) & BLK-3 (Exposed Config)
1. **Rotate Exposed Credentials**:
   ```bash
   # Remove exposed token in .fly/config.yml
   flyctl auth logout
   ```
2. **Generate Org-Scoped Token**:
   - Create org token with deploy permissions for the RAE Fly.io organization.
   - Set environment secret in GitHub repository:
     ```bash
     gh secret set FLY_API_TOKEN --body "$ORG_SCOPED_FLY_TOKEN" --repo bshelby88/nimbus-agent
     ```
3. **Inject Credentials into Docker Container Environment**:
   Update `fly.toml` for `staci-core` and `nimbus-agent` to include explicit environment secret bindings:
   ```toml
   [env]
     NODE_ENV = "production"
     PORT = "8080"

   [secrets]
     FLY_API_TOKEN = "env:FLY_API_TOKEN"
     AIRTABLE_API_KEY = "env:AIRTABLE_API_KEY"
     HMAC_SECRET_KEY = "env:HMAC_SECRET_KEY"
   ```

---

## Module 3: AEK Kernel v0.4 Database & Task Lease Engine Setup

### Deploying Row-Locking Skip-Lock Queue in FastAPI
To prevent task claiming race conditions and "ACK without execution" traps, implement `FOR UPDATE SKIP LOCKED` query semantics in PostgreSQL:

```python
# rae_aek/db/queue.py
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def lease_next_task(session: AsyncSession, agent_id: str, lease_duration_sec: int = 300):
    query = text("""
        UPDATE tasks
        SET 
            status = 'LEASED',
            assigned_agent = :agent_id,
            leased_at = NOW(),
            expires_at = NOW() + INTERVAL '1 second' * :duration
        WHERE id = (
            SELECT id FROM tasks
            WHERE status = 'PENDING' OR (status = 'LEASED' AND expires_at < NOW())
            ORDER BY priority DESC, created_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        )
        RETURNING id, title, payload, priority;
    """)
    result = await session.execute(query, {"agent_id": agent_id, "duration": lease_duration_sec})
    await session.commit()
    return result.fetchone()
```

---

## Module 4: Persistent Volume Configuration for Agent Memory

### Fixing Ephemeral State Loss (BLK-7 Resolution)
Add persistent Fly volume definitions to `fly.toml` for `bean-agent` and `staci-core` to retain SQLite databases (`agent_memory.db`) across machine restarts:

```toml
# fly.toml snippet for bean-agent
[[mounts]]
  source = "bean_memory_vol"
  destination = "/data"
  initial_size = "1gb"
```

Configure SQLite path in agent runtime:
```javascript
// bean-poller.js
const dbPath = process.env.DATABASE_PATH || '/data/agent_memory.db';
const db = new Database(dbPath);
```

---

## Module 5: Monetization Endpoint Wiring (Dispute Forge & Sentry Forge)

### Wiring Sentry Forge $5/Case x402 Base USDC Endpoint
Create `/api/analyze-case` route with mandatory x402 payment header verification:

```python
# sentry_forge/main.py
from fastapi import FastAPI, Header, HTTPException, Depends
from sentry_forge.payment import verify_base_usdc_payment

app = FastAPI(title="Sentry Forge x402 API")

@app.post("/api/analyze-case")
async def analyze_legal_case(
    case_data: dict,
    x_402_payment: str = Header(..., alias="X-402-Payment-Tx")
):
    # Verify Base network USDC transfer to 0x9e6A (minimum $5.00 USDC)
    is_valid, amount = await verify_base_usdc_payment(x_402_payment, min_amount=5.00)
    if not is_valid:
        raise HTTPException(status_code=402, detail="Payment Required: Valid $5 Base USDC tx required")
    
    # Process case analysis via Anthropic Haiku
    analysis = await process_haiku_legal_defense(case_data)
    return {"status": "success", "analysis": analysis, "verified_payment_usdc": amount}
```

---

## Module 6: Daily Verification & Telemetry Cron Setup

### Cron Health Callback Verification
Add programmatic callback reporting to all daily self-ping GitHub Actions workflows:

```yaml
# .github/workflows/daily_self_ping.yml
name: Verified Daily Self-Ping
on:
  schedule:
    - cron: '0 12 * * *'

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping x402 Bazaar Endpoint
        id: ping_step
        run: |
          RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://tradingagents-x402.fly.dev/health)
          if [ "$RESPONSE" -eq 200 ]; then
            echo "STATUS=SUCCESS" >> $GITHUB_ENV
          else
            echo "STATUS=FAILED" >> $GITHUB_ENV
            exit 1
          fi

      - name: Report Telemetry to AEK Kernel
        if: always()
        run: |
          curl -X POST https://rae-aek.fly.dev/v1/events \
            -H "Content-Type: application/json" \
            -H "X-HMAC-Signature: ${{ secrets.HMAC_KEY }}" \
            -d "{\"event\": \"ping.check\", \"status\": \"${{ env.STATUS }}\", \"service\": \"tradingagents-x402\"}"
```
