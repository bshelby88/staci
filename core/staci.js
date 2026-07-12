/* staci-core — the one mind. Loop: poll → plan → act → verify → ledger.
 * Runs on 2 Fly machines / 2 regions. GitHub Actions is her hands:
 * she opens PRs and merges; CI deploys. She never shells fly/gh herself.
 * State: Postgres (SUPABASE_URL). Approvals: Telegram buttons.
 * DRY_RUN=1 (default) logs intended actions without executing. */
"use strict";
const k = require("@staci/kernel");
const u = require("@staci/kernel/src/unison.js");

const CFG = {
  dryRun: process.env.DRY_RUN !== "0",
  pollMs: Number(process.env.POLL_MS || 60000),
  treasury: process.env.TREASURY || "0x6bDea25c368c32eeCb31054dd4766Fc8125e4e02",
  rpcUrl: process.env.BASE_RPC_URL || "https://mainnet.base.org",
  dbUrl: process.env.SUPABASE_URL || null,   // tasks/runs/events tables
  telegram: process.env.TELEGRAM_BOT_TOKEN || null,
};

const ROLES = {
  planner:  "Decompose goals into tasks with acceptance criteria (a public URL or tx hash).",
  builder:  "Execute one task. May not mark done.",
  verifier: "Fetch the acceptance URL/tx independently. Only a verifier marks done.",
  publisher:"Registry-sync + announcements after verified deploys.",
};

async function ledgerTick() {
  try {
    const { totalUsdc, transfers } = await k.revenueFromChain({
      treasury: CFG.treasury, rpcUrl: CFG.rpcUrl,
      fromBlock: "0x" + Math.max(0, Number(process.env.LEDGER_FROM_BLOCK || 0)).toString(16),
    });
    console.log(`[LEDGER:CHAIN] treasury=${CFG.treasury} totalUsdc=${totalUsdc} txs=${transfers.length}`);
    return { totalUsdc, transfers };
  } catch (e) {
    console.warn(`[LEDGER:CHAIN] read failed (never fabricate): ${e.message}`);
    return null;
  }
}

function makeBridge() {
  if (!process.env.AIRTABLE_TOKEN) return null; // board offline mode
  return u.createAirtableBridge({
    token: process.env.AIRTABLE_TOKEN,
    baseId: process.env.AIRTABLE_BASE || "appHjVD4pMobyUyNj",
    tableId: process.env.AIRTABLE_TABLE || "tblWmov5XSkSh9xdE",
  });
}

/** One unison cycle: heartbeat -> election -> (if elected) triage board. */
async function unisonTick(bridge, heartbeats) {
  heartbeats.staci = Date.now();
  const { elected, reason } = u.electExecutor(heartbeats);
  if (elected !== "staci") {
    console.log(`[UNISON] standing by (${elected || "none"} elected: ${reason})`);
    return;
  }
  if (!bridge) return console.log("[UNISON] elected, but no AIRTABLE_TOKEN — board offline");
  const records = await bridge.list(25);
  for (const rec of records) {
    const status = rec.fields[u.FIELDS.status];
    const statusName = status && status.name ? status.name : status;
    const title = rec.fields[u.FIELDS.title] || "";
    if (statusName === "queued") {
      const route = u.routeTask(title, rec.fields[u.FIELDS.instructions] || "");
      if (route.to === "staci") {
        const claim = await u.claimTask(bridge, rec.id, "staci");
        if (claim.claimed) {
          console.log(`[UNISON] claimed: ${title.slice(0, 60)}`);
          if (CFG.dryRun) console.log("[UNISON] DRY_RUN — would execute via PR -> CI");
          // real path: open PR, wait for green Actions, completeTask(bridge, rec.id, "staci", healthUrl)
        }
      }
    }
    if (statusName === "deploying") {
      const env = u.parseEnvelope(rec.fields[u.FIELDS.notes]) || {};
      if (env.verification_url && env.built_by && env.built_by !== "staci") {
        const v = await u.verifyTask(bridge, rec.id, "staci").catch((e) => ({ done: false, detail: e.message }));
        console.log(`[UNISON] verified '${title.slice(0, 50)}': ${v.done ? "DONE" : v.detail}`);
      }
    }
  }
}

const http = require("node:http");
http.createServer((_, res) => {
  res.setHeader("content-type", "application/json");
  res.end(JSON.stringify({ status: "ok", service: "staci-core", ts: new Date().toISOString() }));
}).listen(Number(process.env.PORT) || 3000);

async function loop() {
  console.log(`staci-core up · dryRun=${CFG.dryRun} · roles=${Object.keys(ROLES).join(",")}`);
  const bridge = makeBridge();
  const heartbeats = { staci: Date.now(), nimbus: 0 }; // nimbus writes its own via envelope
  for (;;) {
    await ledgerTick();
    await unisonTick(bridge, heartbeats).catch((e) => console.warn(`[UNISON] tick error: ${e.message}`));
    await new Promise((r) => setTimeout(r, CFG.pollMs));
  }
}
if (require.main === module) loop();
module.exports = { ROLES, ledgerTick, CFG };
