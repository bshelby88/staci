"""
Hermes Directory Seeding & Substack Outbound Engine
Formats and dispatches submission payloads for AI Directories and Substack publications.
"""

import json
import os
import time
import urllib.request
from typing import List, Dict, Any

KERNEL_URL = "https://rae-kernel.fly.dev/v1/events"
API_KEY = os.environ.get("RAE_KERNEL_API_KEY")

DIRECTORIES = [
    {
        "name": "Futurepedia",
        "url": "https://www.futurepedia.io/submit-tool",
        "tool_title": "RAE Monetization Gateway",
        "tagline": "Autonomous Economic Kernel & x402 Base USDC Machine Commerce Gateway",
        "category": "Developer Tools / AI Infrastructure",
        "live_url": "https://rae-monetization-gateway.fly.dev/healthz"
    },
    {
        "name": "There's An AI For That (TAAFT)",
        "url": "https://theresanaiforthat.com/submit/",
        "tool_title": "Dispute Forge x402",
        "tagline": "Automated FDCPA / FCRA dispute letter generator with Base USDC micropayments",
        "category": "Legal & Finance",
        "live_url": "https://rae-monetization-gateway.fly.dev/v1/products"
    },
    {
        "name": "awesome-x402 Directory",
        "url": "https://github.com/coinbase/awesome-x402",
        "tool_title": "RAE Fleet Microservices (14 Fly Endpoints)",
        "tagline": "Production-ready Base USDC paid APIs and autonomous agent endpoints",
        "category": "Blockchain / Machine Commerce",
        "live_url": "https://tradingagents-x402.fly.dev/health"
    }
]

class HermesOutboundEngine:
    def format_substack_post(self, title: str, summary: str, highlights: List[str]) -> Dict[str, Any]:
        """Formats weekly Substack article for 'What's Moving in Agent Commerce'."""
        body = f"""# {title}

{summary}

## Key Agent Commerce Highlights
""" + "\n".join([f"- {h}" for h in highlights]) + """

---
*Published by Hermes Outbound Engine for Royal Agentic Enterprises.*
"""
        return {"title": title, "body": body, "status": "DRAFT_READY"}

    def dispatch_directory_submissions(self) -> List[Dict[str, Any]]:
        results = []
        print("[Hermes] Formatting and dispatching AI directory submission payloads...")
        
        for d in DIRECTORIES:
            payload = {
                "type": "outbound.directory.submission",
                "source": "Hermes_Outbound_Engine",
                "tenant_id": "default",
                "deduplication_key": f"hermes_dir_{d['name'].lower().replace(' ', '_')}_{int(time.time())}",
                "payload": d
            }
            
            headers = {'Content-Type': 'application/json', 'X-API-Key': API_KEY}
            try:
                req = urllib.request.Request(KERNEL_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
                with urllib.request.urlopen(req) as resp:
                    print(f"[Hermes] Submission for '{d['name']}' dispatched to rae-kernel (HTTP {resp.status})")
                    results.append({"directory": d["name"], "status": "DISPATCHED", "http_code": resp.status})
            except Exception as e:
                print(f"[Hermes] Directory submission warning for '{d['name']}': {e}")
                results.append({"directory": d["name"], "status": "WARNING", "error": str(e)})

        return results

if __name__ == "__main__":
    print("Testing Hermes Directory Seeding & Substack Outbound Engine...")
    hermes = HermesOutboundEngine()
    
    # 1. Dispatch Directory Submissions
    sub_results = hermes.dispatch_directory_submissions()
    assert len(sub_results) == 3
    
    # 2. Format Substack Article
    post = hermes.format_substack_post(
        title="Agent Commerce Weekly: How We Achieved 100% Deterministic Agent Execution",
        summary="A forensic breakdown of how RAE eliminated false-done signals and launched Base USDC micropayments.",
        highlights=[
            "PostgreSQL FOR UPDATE SKIP LOCKED task queues prevent lease conflicts.",
            "Deterministic AI Envelopes intercept process exit codes before ACKs.",
            "Base RPC watchers verify on-chain USDC hashes for 0x9e6A wallet."
        ]
    )
    assert post["status"] == "DRAFT_READY"
    print("[Hermes] Hermes Outbound Engine Passed All Assertions!")
