---
name: kc-competitive-analysis
description: Use when running China peer competitive analysis for a private company (placeholder KC) against A-share/HK listed peers with free AkShare data, producing matrix + narrative skeleton or a Canvas.
---

# kc-competitive-analysis

Free-tier China peer benchmarking: private company overlay (default name **KC**) vs listed peers via AkShare. Do **not** require packaging an MCP into the project—call AkShare (or an already-installed market-data MCP if present).

## Inputs

1. **Subject company** — default label `KC`. Private financials from a local overlay file (JSON/CSV/xlsx/docx sample statements). Never invent KC numbers.
2. **Peer list** — A-share and/or HK codes + short names. If missing, ask once or use the caller’s last peer set.
3. **Year** — default latest full fiscal year available.
4. **Deliverable** — markdown skeleton and/or interactive Page (Canvas). Prefer Page when the user wants charts/toggles.

## Data sources (priority)

| Layer | Source | Notes |
|---|---|---|
| A-share statements | AkShare / optional ashare-style peer compare | Assets, revenue, parent NI, OCF, equity, ROE |
| A-share mix | `stock_zygc_em` + cninfo profile | Product/region mix; MD&A via annual-report PDF if API fails |
| HK peers | `stock_financial_hk_analysis_indicator_em` | Align currency; OCF may be estimated from OCF/sales |
| KC | User overlay only | Same units as peers; mark missing fields |

Do **not** vendor MCP server code into the analysis repo. Document optional MCP as “if connected, prefer it; else AkShare scripts.”

## Steps

1. **Resolve tickers** — Map peer names → A/HK codes; exclude non-covered markets from the numeric matrix (placeholder row OK).
2. **Pull listed peers** — Run free pulls for the year; write JSON under `data/`.
3. **Load KC overlay** — From `examples/kc-placeholder/kc_financials.sample.json` shape (or user path). Fail clearly if all nulls.
4. **Build matrix** — One table: KC + peers. Columns: revenue, parent NI, OCF, assets, equity, ROE; add gross margin / SG&A rates when available. Flag HK/KC口径差异.
5. **Narrative** — Per peer: business tag + 1–2 mix bullets; KC: role vs peers (e.g. brand / retailer / agency) from user notes only.
6. **Competitive map** — Mode tags + “relative to KC” one-liners.
7. **Deliver** — `examples/<slug>/skeleton.md` and optional Page (metric switch, include-HK toggle, scatter revenue×ROE). Chat: link + one-line takeaway, not the full body.
8. **Gaps** — List what failed (cninfo API, missing KC fields, HK balance sheet) and next free step.

## Output skeleton headings

1. Universe  
2. Financial matrix  
3. Business narrative  
4. Competitive map  
5. Profitability & expense rates (optional)  
6. Gaps / next free steps  

## Anti-patterns

- Do not publish KC figures externally or to a public MCP.
- Do not hard-code one industry’s peers into the skill; peers come from the run.
- Do not treat Canvas as the source of truth—repo/`data/` + overlay are.
