# DRL Odds Engine

## Ownership

The Odds Engine is an independent DRL backend service at
`backend/dfm/drl/core/odds_engine/`. It owns probability calculation, fair
decimal-price conversion, market revision validation and the audit-event contract.
It is not part of Newsroom and is not part of the Fantasy Engine.

Newsroom, Match Centre, competition ladders and other DRL features are consumers.
They must request a calculation through the Odds Engine boundary and must not
reimplement or mutate pricing logic.

## Initial market types

- **Head-to-Head:** two-franchise result distribution from supplied projected scores.
- **Premiership:** a full-field distribution across exactly 17 supplied NRL club power ratings.
- **Man of the Match:** player distribution from supplied projected fantasy scores.

All probabilities are normalised. Decimal prices are fair inverse probabilities
(`1 / probability`); no bookmaker margin or wagering integration is included.

## Model limitations

The H2H logistic scale and the Premiership / Man of the Match softmax temperatures
are explicit starting parameters, not trained or calibrated coefficients. The
service does not fabricate club ratings, player projections, fixtures, injuries,
line-ups or historical performance. Those inputs must be supplied by verified DRL
competition-intelligence adapters. Historical backtesting and calibration are
required before treating model outputs as production-grade forecasts.

## Evidence and official revisions

Every calculation carries a source identifier, category, evidence status,
confidence tier and summary. Rumour and unverified inputs can produce indicative
calculations only. Only a verified source with a verified confidence tier is
eligible to produce an official market calculation or price-movement audit event.

Audit events are immutable domain records with deterministic idempotency keys,
revision numbers, model version, source provenance, previous/revised probability
and previous/revised decimal price. The persistence interface is append-only and
must be backed by a database implementation with insert-only privileges and
appropriate row-level security before production use.

## API and security boundary

The FastAPI router is created through `create_router()` and requires the host
application to inject both an authorization dependency and an engine provider.
There is no default public router, database client, secret, external API or
unauthenticated endpoint in this package. The host application must enforce
league/competition-level authorization before mounting or invoking it.

## Persistence and deployment status

This implementation contains pure calculation services and a persistence port.
It deliberately does not add a Supabase migration, production database table,
deployment route or Cloudflare configuration. Those require separate schema
verification and deployment authorization.
