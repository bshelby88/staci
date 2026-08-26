"""
Base NFT 7.5% Creator Royalty Collector Engine
Tracks secondary Base NFT marketplace sales and routes creator royalties to wallet 0x9e6A.
"""

import json
import time
import urllib.request
from typing import Dict, Any, List, Optional

from credential_config import require_kernel_api_key

TARGET_WALLET = "0x9e6A95B5Bf1190B5aCD00508a8E9c72eDEd5fB60"
ROYALTY_BPS = 750 # 7.5% creator fee
KERNEL_URL = "https://rae-kernel.fly.dev/v1/events"

class NFTRoyaltyCollector:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = require_kernel_api_key(api_key)

    def calculate_royalty(self, sale_price_eth: float) -> float:
        return round(sale_price_eth * (ROYALTY_BPS / 10000), 5)

    def process_secondary_sale(self, token_id: int, collection_name: str, sale_price_eth: float, buyer: str, seller: str) -> Dict[str, Any]:
        royalty_eth = self.calculate_royalty(sale_price_eth)
        print(f"[RoyaltyCollector] Secondary sale detected for {collection_name} #{token_id}: {sale_price_eth} ETH. Royalty fee (7.5%): {royalty_eth} ETH")

        royalty_data = {
            "token_id": token_id,
            "collection": collection_name,
            "sale_price_eth": sale_price_eth,
            "royalty_eth": royalty_eth,
            "royalty_bps": ROYALTY_BPS,
            "treasury_wallet": TARGET_WALLET,
            "buyer": buyer,
            "seller": seller,
            "timestamp": int(time.time())
        }

        # Dispatch royalty telemetry event to rae-kernel
        payload = {
            "type": "nft.royalty.collected",
            "source": "NFT_Royalty_Collector",
            "tenant_id": "default",
            "deduplication_key": f"royalty_{collection_name.lower()}_{token_id}_{int(time.time())}",
            "payload": royalty_data
        }

        headers = {'Content-Type': 'application/json', 'X-API-Key': self.api_key}
        try:
            req = urllib.request.Request(KERNEL_URL, data=json.dumps(payload).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req) as resp:
                print(f"[RoyaltyCollector] Royalty event dispatched to rae-kernel (HTTP {resp.status})")
                return {"status": "success", "http_code": resp.status, "royalty_data": royalty_data}
        except Exception as e:
            print(f"[RoyaltyCollector] Royalty dispatch warning: {e}")
            return {"status": "warning", "error": str(e), "royalty_data": royalty_data}

if __name__ == "__main__":
    print("Testing Base NFT Creator Royalty Collector Engine...")
    collector = NFTRoyaltyCollector()
    res = collector.process_secondary_sale(
        token_id=7,
        collection_name="COIN Boots",
        sale_price_eth=0.50, # 0.50 ETH secondary sale
        buyer="0x2222222222222222222222222222222222222222",
        seller="0x3333333333333333333333333333333333333333"
    )
    assert res["status"] == "success"
    assert res["royalty_data"]["royalty_eth"] == 0.0375 # 7.5% of 0.5 ETH
    print("Base NFT Creator Royalty Collector Engine Passed All Assertions!")
