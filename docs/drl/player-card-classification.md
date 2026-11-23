# DRL Player Card Classification and Milestones

## Career milestone cards

Career milestone cards are based only on a verified all-time NRL appearance total, not the selected-season `appearances` statistic.

| Career NRL appearances | Card | Display colour |
|---:|---|---|
| 0–49 | White | `#F4F4F4` |
| 50–99 | Mint | `#A8E8CE` |
| 100–149 | Neon Lime | `#B7FF00` |
| 150–299 | Emerald Green | `#087F45` |
| 300+ | Platinum | Metallic platinum |

A player retains every milestone card earned. The profile derives the full earned milestone collection from the verified career total, so a player at 300 appearances displays all five milestone cards.

## Independent achievement cards

These cards are independent of NRL career appearance totals and may coexist with every career milestone card:

- Gold — 1st place
- Silver — 2nd place
- Bronze — 3rd place
- State of Origin — Blue
- State of Origin — Burgundy

Achievement cards are displayed only when a verified record exists in the private achievement-card table. Each record requires an HTTPS evidence URL and reviewer identity/timestamp.

## Data integrity and security

- `drl_nrl_player_season_stats.appearances` is season-scoped and must never be used as a career total.
- All-time totals are stored separately in `dfm_private.drl_nrl_player_career_totals`.
- Career totals are not returned to the frontend until marked verified with reviewer and verification timestamp.
- Unverified career totals produce no milestone card; the UI explicitly reports that the career total is unverified.
- Origin and podium cards are sourced from a separate private achievement table and require verified evidence.
- Private tables have RLS enabled and no browser-role table privileges.
- The authenticated Worker calls the restricted RPC; private database object names and credentials are not exposed to the browser.
- The migration is source-controlled only. It has not been applied to JARVIS, and no career or achievement records have been fabricated.

## Prestige order

1. Gold
2. Silver
3. Bronze
4. Platinum
5. State of Origin Blue and State of Origin Burgundy (equal rank)
6. Emerald Green
7. Neon Lime
8. Mint
9. White

This is a display hierarchy only. It does not overwrite or remove any card already earned.
