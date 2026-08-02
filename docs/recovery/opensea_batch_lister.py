"""
OpenSea Base NFT Batch Listing & Metadata Generator
Formats and prepares OpenSea storefront listing payloads for all 22 minted Base NFTs.
"""

import json
from datetime import datetime, timezone

BASE_CHAIN_ID = 8453
WALLET_ADDRESS = "0x9e6A95B5Bf1190B5aCD00508a8E9c72eDEd5fB60"

NFT_CATALOG = [
    {"id": f"nft_wisdom_{i:02d}", "name": f"RAE Wisdom Drop #{i:02d}", "type": "Wisdom Drop", "price_eth": 0.02}
    for i in range(1, 13)
] + [
    {"id": f"nft_boot_{i:02d}", "name": f"COIN Boots Asset #{i:02d}", "type": "COIN Boots", "price_eth": 0.05}
    for i in range(1, 11)
]

def generate_opensea_listings():
    listings = []
    for item in NFT_CATALOG:
        listing = {
            "asset_id": item["id"],
            "name": item["name"],
            "collection": "Royal Agentic Enterprise Shelf Assets",
            "chain": "Base",
            "chain_id": BASE_CHAIN_ID,
            "seller_wallet": WALLET_ADDRESS,
            "listing_price_eth": item["price_eth"],
            "currency": "ETH",
            "expiration_days": 30,
            "opensea_order_payload": {
                "maker": WALLET_ADDRESS,
                "listingTime": int(datetime.now(timezone.utc).timestamp()),
                "expirationTime": int(datetime.now(timezone.utc).timestamp()) + (30 * 86400),
                "priceWei": str(int(item["price_eth"] * 10**18))
            }
        }
        listings.append(listing)
    return listings

if __name__ == "__main__":
    print("Generating OpenSea Batch Listing Manifest for 22 Base NFTs...")
    payloads = generate_opensea_listings()
    assert len(payloads) == 22
    
    with open("opensea_22_nft_listings.json", "w") as f:
        json.dump(payloads, f, indent=2)

    print(f"Successfully generated {len(payloads)} OpenSea Base NFT listing payloads!")
    print("Saved manifest to opensea_22_nft_listings.json")
