# Staci
One mind. One repo. One ledger (the chain). Royal Agentic Enterprises' autonomous x402 fleet.

- `/kernel` — @staci/kernel: honesty-by-construction results, chain-derived revenue, discovery generation, receipts, facilitator failover. 14 tests.
- `/services/<name>` — each x402 service, ~80 lines on the kernel. tradingagents ported (8 py tests).
- `/core` — staci-core loop (DRY_RUN by default until Postgres + Telegram bootstrap).
- `/.github/workflows` — deploy (tests must pass → flyctl → verify URLs) + 15-min watchdog.

Bootstrap (one time, tonight): install FLY_API_TOKEN + GH_PAT as repo secrets. After that, no laptop, ever.
Charter: Drive 1miKFGIU41pjtJ0dZhSkY1cVZn32b5IGB · Architecture: Drive 1mGHlCWbK7FZT-V_w6Xq0rTPdC-7xoC1E
Kill-gate: every service earns $25 external within 30 days of listing or the watchdog suspends it.
