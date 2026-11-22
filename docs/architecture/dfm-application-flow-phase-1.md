# DFM Application Flow — Phase 1

## Purpose

Establish the visible application navigation and screen architecture before backend, database, authentication, business logic or infrastructure implementation.

## DFM headquarters

- DFM HQ is the root application destination.
- Club Ownership & Management opens the management-simulation interface foundation.
- Franchise HQ remains closed and is not reachable from the DFM home screen.
- Newsroom is present as a destination with an explicit not-connected state.
- Digital Rugby League links to the existing DRL environment.
- Digital Rugby League Women's has a reserved destination with an explicit interface-foundation state.

## Club Ownership & Management navigation

1. Overview
2. Franchise Progress
3. Season History
4. Historical Recognition
5. Asset Portfolio
6. Asset Development
7. Finances

### Franchise progression

The five classifications are:

1. Community Franchise
2. Regional Franchise
3. Championship Franchise
4. National Franchise
5. Premier Franchise

A newly created franchise starts at Community Franchise. One completed, recognised season advances the franchise by one rank in that sport. Each sport maintains an independent season and progression record. Premier Franchise is the maximum classification; additional completed seasons may continue to earn development rewards.

### Founding-franchise recognition

Select franchises that participated in the user's competition from 2019 may be eligible for historical recognition. Historical seasons and achievements must be verified before credits are calculated or applied. Historical progression credits and historical award points are separate concepts. No historical teams, seasons, awards or balances are fabricated in the interface.

### Asset development

Each asset has an independent upgrade path. Asset maximums may be three or five levels depending on the asset type.

| Asset category | Maximum | Level 1 | Maximum-level example |
|---|---:|---|---|
| Stadium & Grounds | 5 | Local Playing Field | Elite Stadium |
| Training & Academy | 5 | Empty Training Field | Academy of Excellence |
| Hospitality | 5 | Local Pub | Leagues Club |
| Accommodation | 5 | Local 1-Star Motel | 5-Star Luxury Hotel |
| Administration | 5 | Clubhouse | Franchise HQ Office Building |
| Transport | 3 | Team Van | Team Coach |
| Medical | 3 | First-Aid Room | Sports Medicine Centre |
| Recovery | 3 | Basic Recovery Room | Elite Recovery Centre |

Asset progression is independent of franchise classification. The interface presents planned catalogues only; it does not represent any asset as purchased.

## Existing DRL environment

The existing DRL dashboard and its current navigation are preserved in this phase. Fixture, ladder, awards, player and financial information remain explicitly disconnected until their authorised services are implemented.

## Phase 1 boundaries

- Frontend navigation, screen structure and responsive interface only.
- No Supabase/JARVIS schema or data changes.
- No Cloudflare configuration or deployment changes.
- No authentication or backend implementation.
- No fabricated live data, balances, purchases, historical points or sporting results.
- Franchise HQ remains closed.
- No merge or production deployment.
