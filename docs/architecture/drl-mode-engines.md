# DRL Classic and Draft Engine Boundaries

## Ownership

Classic and Draft independently own their Odds, Awards, Newsroom and Ladder engines under their respective mode directories. No mode engine, calculation service, award history, odds history, newsroom feed or standings implementation is shared. The packages do not import one another.

- Classic: `backend/dfm/sports/drl/classic/core/{odds_engine,awards_engine,newsroom,ladder_engine}/`
- Draft: `backend/dfm/sports/drl/draft/core/{odds_engine,awards_engine,newsroom,ladder_engine}/`

## Awards

MOTR has priority over MOTM. The MOTR fixture does not receive a separate MOTM, yielding one MOTR plus six MOTM awards in a seven-fixture round. Finalisation waits until every assigned fixture is complete and verified. Classic shared-player ownership is resolved by full fantasy team total for the award period; tied totals share the award. Draft ownership is independent.

Player points: MOTM 2, MOTR 3, and Draft-only TOTW 1. Achievements remain recorded, but only the highest-value award per player per round earns points. Coach credits snapshot the coach and franchise at award time, so transfers never rewrite earlier credits. Play of the Week is recorded as an achievement only until its criteria and points are confirmed.

Draft TOTW and TOTY use a positional XIII: WFB 3, CTR 2, HLF 2, EDG 2, MID 3, HOK 1. TOTW requires the player's score to have contributed to the franchise total. DPP primary positions are filled before secondary positions. The final-slot tie-break is player score, franchise weekly total, then the player's real-world NRL team points; a complete tie shares selection.

## Odds

Markets are DRL fantasy-competition probabilities and fair decimal prices, not bookmaker markets or NRL club win markets. H2H uses supplied fantasy-score projections. Premiership and award winner markets use supplied projections. Finals and Grand Final qualification are separate yes/no markets per franchise. Parameters are transparent heuristics and require historical backtesting before production-grade forecasts are claimed.

## Newsroom and ladders

Each mode has a separate article repository boundary and feed. Match reports require completed fixtures and verified statistics. Weekly award coverage is published together only after the whole round is finalised. Each mode calculates its own competition ladder, player-awards ladder and coach-awards ladder. Competition points are supplied by the configured competition rules; this engine does not assume a points schedule. Award ladders retain category columns and totals; player ladders support positional filtering.

## Persistence and deployment

Persistence is represented by injected repository interfaces. No live JARVIS schema or table names are assumed, and no migrations, credentials, Cloudflare settings or production routes are added. API mounting requires a separately verified authenticated host integration.
