/**
 * Server-only DRL persistence adapter.
 *
 * Inject an authenticated Supabase server client configured with the
 * service-role credential from the runtime secret store. Never construct
 * this adapter in browser code and never expose the credential to clients.
 * The adapter calls only service_role-restricted public RPC wrappers; it
 * never addresses dfm_private through PostgREST.
 */
export type DrlMode = "classic" | "draft";

export interface RpcError {
  message: string;
}

export interface RpcResult<T = unknown> {
  data: T | null;
  error: RpcError | null;
}

export type DfmRpcExecutor = (
  functionName: string,
  args: Record<string, unknown>
) => Promise<RpcResult>;

export interface MarketOutcomeInput {
  selectionId: string;
  label: string;
  probability: number;
  decimalPrice: number;
}

export interface PriceMovementInput {
  marketId: string;
  selectionId: string;
  revision: number;
  previousProbability: number;
  revisedProbability: number;
  previousPrice: number;
  revisedPrice: number;
  sourceId: string;
  modelVersion: string;
  idempotencyKey: string;
}

export interface MarketSnapshotInput {
  leagueId: string;
  marketId: string;
  marketType: string;
  revision: number;
  source: {
    sourceId: string;
    category: string;
    verified: boolean;
    summary: string;
  };
  modelVersion: string;
  official: boolean;
  outcomes: readonly MarketOutcomeInput[];
  movements?: readonly PriceMovementInput[];
}

export interface AwardRecordInput {
  awardId: string;
  category: string;
  roundNumber: number;
  playerId: string;
  playerName: string;
  franchiseId: string;
  coachId: string;
  baseScore: number;
  points: number;
  position?: string | null;
  achievementOnly?: boolean;
}

export interface CoachCreditInput {
  coachId: string;
  franchiseId: string;
  playerId: string;
  category: string;
  roundNumber: number;
  points: number;
}

export interface NewsArticleInput {
  articleId: string;
  leagueId: string;
  roundNumber: number;
  category: string;
  title: string;
  summary: string;
  content: string;
  published?: boolean;
}

export interface LadderResultInput {
  leagueId: string;
  fixtureId: string;
  homeFranchiseId: string;
  awayFranchiseId: string;
  homeScore: number;
  awayScore: number;
  homeCompetitionPoints: number;
  awayCompetitionPoints: number;
  finalised: boolean;
}

function required(value: string, field: string): void {
  if (!value.trim()) throw new TypeError(field + " must not be blank");
}

function finiteNonNegative(value: number, field: string): void {
  if (!Number.isFinite(value) || value < 0) {
    throw new TypeError(field + " must be finite and non-negative");
  }
}

function mapMovement(value: PriceMovementInput): Record<string, unknown> {
  return {
    selection_id: value.selectionId,
    revision: value.revision,
    previous_probability: value.previousProbability,
    revised_probability: value.revisedProbability,
    previous_price: value.previousPrice,
    revised_price: value.revisedPrice,
    source_id: value.sourceId,
    model_version: value.modelVersion,
    idempotency_key: value.idempotencyKey
  };
}

abstract class ModePersistenceAdapter {
  protected abstract readonly mode: DrlMode;
  protected abstract readonly rpcNames: {
    market: string;
    awards: string;
    newsroom: string;
    ladder: string;
    appendMovement: string;
    listMovements: string;
    listAwards: string;
    listCredits: string;
    listNews: string;
    listLadder: string;
  };

  constructor(private readonly rpc: DfmRpcExecutor) {}

  async persistMarketSnapshot(input: MarketSnapshotInput): Promise<string> {
    required(input.leagueId, "leagueId");
    required(input.marketId, "marketId");
    required(input.modelVersion, "modelVersion");
    required(input.source.sourceId, "source.sourceId");
    required(input.source.category, "source.category");
    required(input.source.summary, "source.summary");

    if (!Number.isInteger(input.revision) || input.revision < 1) {
      throw new TypeError("revision must be a positive integer");
    }
    if (input.official !== input.source.verified) {
      throw new TypeError("official must match source verification");
    }
    if (input.outcomes.length < 2) {
      throw new TypeError("at least two market outcomes are required");
    }

    const selectionIds = new Set<string>();
    let probabilityTotal = 0;
    for (const outcome of input.outcomes) {
      required(outcome.selectionId, "outcome.selectionId");
      required(outcome.label, "outcome.label");
      if (selectionIds.has(outcome.selectionId)) {
        throw new TypeError("market outcome selection IDs must be unique");
      }
      selectionIds.add(outcome.selectionId);
      if (!Number.isFinite(outcome.probability) ||
          outcome.probability <= 0 || outcome.probability >= 1) {
        throw new TypeError("outcome probability must be between zero and one");
      }
      if (!Number.isFinite(outcome.decimalPrice) || outcome.decimalPrice < 1) {
        throw new TypeError("decimal price must be finite and at least one");
      }
      probabilityTotal += outcome.probability;
    }
    if (Math.abs(probabilityTotal - 1) > 1e-8) {
      throw new TypeError("market probabilities must sum to one");
    }

    const movements = input.movements ?? [];
    for (const movement of movements) {
      if (movement.revision !== input.revision) {
        throw new TypeError("price movement revision must match snapshot revision");
      }
      required(movement.idempotencyKey, "movement.idempotencyKey");
      required(movement.sourceId, "movement.sourceId");
      required(movement.modelVersion, "movement.modelVersion");
      for (const [field, probability] of [
        ["previousProbability", movement.previousProbability],
        ["revisedProbability", movement.revisedProbability]
      ] as const) {
        if (!Number.isFinite(probability) || probability <= 0 || probability >= 1) {
          throw new TypeError(field + " must be between zero and one");
        }
      }
      for (const [field, price] of [
        ["previousPrice", movement.previousPrice],
        ["revisedPrice", movement.revisedPrice]
      ] as const) {
        if (!Number.isFinite(price) || price < 1) {
          throw new TypeError(field + " must be finite and at least one");
        }
      }
    }

    const result = await this.rpc(this.rpcNames.market, {
      p_league_id: input.leagueId,
      p_market_id: input.marketId,
      p_market_type: input.marketType,
      p_revision: input.revision,
      p_source_id: input.source.sourceId,
      p_source_category: input.source.category,
      p_source_verified: input.source.verified,
      p_source_summary: input.source.summary,
      p_model_version: input.modelVersion,
      p_official: input.official,
      p_outcomes: input.outcomes.map((outcome) => ({
        selection_id: outcome.selectionId,
        label: outcome.label,
        probability: outcome.probability,
        decimal_price: outcome.decimalPrice
      })),
      p_movements: movements.map(mapMovement)
    });
    return this.unwrap<string>(result, "market snapshot");
  }

  async persistAwardBundle(
    leagueId: string,
    awards: readonly AwardRecordInput[],
    credits: readonly CoachCreditInput[]
  ): Promise<number> {
    required(leagueId, "leagueId");
    if (awards.length === 0) throw new TypeError("at least one award is required");

    for (const award of awards) {
      required(award.awardId, "award.awardId");
      required(award.playerId, "award.playerId");
      required(award.playerName, "award.playerName");
      required(award.franchiseId, "award.franchiseId");
      required(award.coachId, "award.coachId");
      finiteNonNegative(award.baseScore, "award.baseScore");
      finiteNonNegative(award.points, "award.points");
      if (!Number.isInteger(award.points)) {
        throw new TypeError("award.points must be an integer");
      }
      if (!Number.isInteger(award.roundNumber) || award.roundNumber < 1) {
        throw new TypeError("award.roundNumber must be a positive integer");
      }
    }
    for (const credit of credits) {
      required(credit.coachId, "credit.coachId");
      required(credit.franchiseId, "credit.franchiseId");
      required(credit.playerId, "credit.playerId");
      finiteNonNegative(credit.points, "credit.points");
      if (!Number.isInteger(credit.points) || credit.points <= 0) {
        throw new TypeError("credit.points must be a positive integer");
      }
      if (!Number.isInteger(credit.roundNumber) || credit.roundNumber < 1) {
        throw new TypeError("credit.roundNumber must be a positive integer");
      }
    }

    const result = await this.rpc(this.rpcNames.awards, {
      p_league_id: leagueId,
      p_awards: awards.map((award) => ({
        award_id: award.awardId,
        category: award.category,
        round_number: award.roundNumber,
        player_id: award.playerId,
        player_name: award.playerName,
        franchise_id: award.franchiseId,
        coach_id: award.coachId,
        base_score: award.baseScore,
        points: award.points,
        position: award.position ?? null,
        achievement_only: award.achievementOnly ?? false
      })),
      p_credits: credits.map((credit) => ({
        coach_id: credit.coachId,
        franchise_id: credit.franchiseId,
        player_id: credit.playerId,
        category: credit.category,
        round_number: credit.roundNumber,
        points: credit.points
      }))
    });
    return this.unwrap<number>(result, "award bundle");
  }

  async appendNewsArticle(article: NewsArticleInput): Promise<boolean> {
    required(article.articleId, "article.articleId");
    required(article.leagueId, "article.leagueId");
    required(article.title, "article.title");
    required(article.summary, "article.summary");
    required(article.content, "article.content");
    if (!Number.isInteger(article.roundNumber) || article.roundNumber < 1) {
      throw new TypeError("article.roundNumber must be a positive integer");
    }

    const result = await this.rpc(this.rpcNames.newsroom, {
      p_league_id: article.leagueId,
      p_article_id: article.articleId,
      p_round_number: article.roundNumber,
      p_category: article.category,
      p_title: article.title,
      p_summary: article.summary,
      p_content: article.content,
      p_published: article.published ?? true
    });
    return this.unwrap<boolean>(result, "newsroom article");
  }

  async persistFinalisedMatch(
    resultInput: LadderResultInput
  ): Promise<boolean> {
    required(resultInput.leagueId, "result.leagueId");
    required(resultInput.fixtureId, "result.fixtureId");
    required(resultInput.homeFranchiseId, "result.homeFranchiseId");
    required(resultInput.awayFranchiseId, "result.awayFranchiseId");
    if (resultInput.homeFranchiseId === resultInput.awayFranchiseId) {
      throw new TypeError("home and away franchises must differ");
    }
    if (!resultInput.finalised) {
      throw new TypeError("only finalised match results can be persisted");
    }
    finiteNonNegative(resultInput.homeScore, "result.homeScore");
    finiteNonNegative(resultInput.awayScore, "result.awayScore");
    finiteNonNegative(resultInput.homeCompetitionPoints, "result.homeCompetitionPoints");
    finiteNonNegative(resultInput.awayCompetitionPoints, "result.awayCompetitionPoints");
    if (!Number.isInteger(resultInput.homeCompetitionPoints) ||
        !Number.isInteger(resultInput.awayCompetitionPoints)) {
      throw new TypeError("competition points must be integers");
    }

    const result = await this.rpc(this.rpcNames.ladder, {
      p_league_id: resultInput.leagueId,
      p_fixture_id: resultInput.fixtureId,
      p_home_franchise_id: resultInput.homeFranchiseId,
      p_away_franchise_id: resultInput.awayFranchiseId,
      p_home_score: resultInput.homeScore,
      p_away_score: resultInput.awayScore,
      p_home_competition_points: resultInput.homeCompetitionPoints,
      p_away_competition_points: resultInput.awayCompetitionPoints
    });
    return this.unwrap<boolean>(result, "finalised match result");
  }


  async appendPriceMovement(
    leagueId: string,
    movement: PriceMovementInput
  ): Promise<boolean> {
    required(leagueId, "leagueId");
    required(movement.marketId, "movement.marketId");
    required(movement.selectionId, "movement.selectionId");
    required(movement.idempotencyKey, "movement.idempotencyKey");
    required(movement.sourceId, "movement.sourceId");
    required(movement.modelVersion, "movement.modelVersion");
    if (!Number.isInteger(movement.revision) || movement.revision < 2) {
      throw new TypeError("movement.revision must be an integer of at least two");
    }
    for (const [field, probability] of [
      ["previousProbability", movement.previousProbability],
      ["revisedProbability", movement.revisedProbability]
    ] as const) {
      if (!Number.isFinite(probability) || probability <= 0 || probability >= 1) {
        throw new TypeError(field + " must be between zero and one");
      }
    }
    for (const [field, price] of [
      ["previousPrice", movement.previousPrice],
      ["revisedPrice", movement.revisedPrice]
    ] as const) {
      if (!Number.isFinite(price) || price < 1) {
        throw new TypeError(field + " must be finite and at least one");
      }
    }
    return this.unwrap<boolean>(await this.rpc(this.rpcNames.appendMovement, {
      p_league_id: leagueId,
      p_market_id: movement.marketId,
      p_selection_id: movement.selectionId,
      p_revision: movement.revision,
      p_previous_probability: movement.previousProbability,
      p_revised_probability: movement.revisedProbability,
      p_previous_price: movement.previousPrice,
      p_revised_price: movement.revisedPrice,
      p_source_id: movement.sourceId,
      p_model_version: movement.modelVersion,
      p_idempotency_key: movement.idempotencyKey
    }), "price movement");
  }

  async listMarketMovements(
    leagueId: string,
    marketId: string
  ): Promise<PriceMovementInput[]> {
    required(leagueId, "leagueId");
    required(marketId, "marketId");
    const rows = this.unwrap<unknown>(await this.rpc(this.rpcNames.listMovements, {
      p_league_id: leagueId,
      p_market_id: marketId
    }), "market history");
    if (!Array.isArray(rows)) throw new Error("Market history returned an invalid payload");
    return rows.map((row) => {
      const value = row as Record<string, unknown>;
      return {
        marketId: String(value.market_id),
        selectionId: String(value.selection_id),
        revision: Number(value.revision),
        previousProbability: Number(value.previous_probability),
        revisedProbability: Number(value.revised_probability),
        previousPrice: Number(value.previous_price),
        revisedPrice: Number(value.revised_price),
        sourceId: String(value.source_id),
        modelVersion: String(value.model_version),
        idempotencyKey: String(value.idempotency_key)
      };
    });
  }

  async listAwards(
    leagueId: string,
    roundNumber?: number
  ): Promise<AwardRecordInput[]> {
    required(leagueId, "leagueId");
    if (roundNumber !== undefined && (!Number.isInteger(roundNumber) || roundNumber < 1)) {
      throw new TypeError("roundNumber must be a positive integer");
    }
    const rows = this.unwrap<unknown>(await this.rpc(this.rpcNames.listAwards, {
      p_league_id: leagueId,
      p_round_number: roundNumber ?? null
    }), "award history");
    if (!Array.isArray(rows)) throw new Error("Award history returned an invalid payload");
    return rows.map((row) => {
      const value = row as Record<string, unknown>;
      return {
        awardId: String(value.award_id),
        category: String(value.category),
        roundNumber: Number(value.round_number),
        playerId: String(value.player_id),
        playerName: String(value.player_name),
        franchiseId: String(value.franchise_id),
        coachId: String(value.coach_id),
        baseScore: Number(value.base_score),
        points: Number(value.points),
        position: value.position === null ? null : String(value.position),
        achievementOnly: Boolean(value.achievement_only)
      };
    });
  }

  async listCoachCredits(
    leagueId: string,
    coachId?: string
  ): Promise<CoachCreditInput[]> {
    required(leagueId, "leagueId");
    const rows = this.unwrap<unknown>(await this.rpc(this.rpcNames.listCredits, {
      p_league_id: leagueId,
      p_coach_id: coachId ?? null
    }), "coach credit history");
    if (!Array.isArray(rows)) throw new Error("Coach credit history returned an invalid payload");
    return rows.map((row) => {
      const value = row as Record<string, unknown>;
      return {
        coachId: String(value.coach_id),
        franchiseId: String(value.franchise_id),
        playerId: String(value.player_id),
        category: String(value.category),
        roundNumber: Number(value.round_number),
        points: Number(value.points)
      };
    });
  }

  async listNewsArticles(
    leagueId: string,
    limit = 25
  ): Promise<NewsArticleInput[]> {
    required(leagueId, "leagueId");
    if (!Number.isInteger(limit) || limit < 1 || limit > 100) {
      throw new TypeError("limit must be an integer from 1 to 100");
    }
    const rows = this.unwrap<unknown>(await this.rpc(this.rpcNames.listNews, {
      p_league_id: leagueId,
      p_limit: limit
    }), "newsroom feed");
    if (!Array.isArray(rows)) throw new Error("Newsroom feed returned an invalid payload");
    return rows.map((row) => {
      const value = row as Record<string, unknown>;
      return {
        articleId: String(value.article_id),
        leagueId: String(value.league_id),
        roundNumber: Number(value.round_number),
        category: String(value.category),
        title: String(value.title),
        summary: String(value.summary),
        content: String(value.content),
        published: Boolean(value.published)
      };
    });
  }

  async listFinalisedMatches(leagueId: string): Promise<LadderResultInput[]> {
    required(leagueId, "leagueId");
    const rows = this.unwrap<unknown>(await this.rpc(this.rpcNames.listLadder, {
      p_league_id: leagueId
    }), "ladder results");
    if (!Array.isArray(rows)) throw new Error("Ladder results returned an invalid payload");
    return rows.map((row) => {
      const value = row as Record<string, unknown>;
      return {
        leagueId,
        fixtureId: String(value.fixture_id),
        homeFranchiseId: String(value.home_franchise_id),
        awayFranchiseId: String(value.away_franchise_id),
        homeScore: Number(value.home_score),
        awayScore: Number(value.away_score),
        homeCompetitionPoints: Number(value.home_competition_points),
        awayCompetitionPoints: Number(value.away_competition_points),
        finalised: Boolean(value.finalised)
      };
    });
  }

  private unwrap<T>(result: RpcResult, operation: string): T {
    if (result.error) {
      throw new Error("DRL " + this.mode + " " + operation +
        " persistence failed: " + result.error.message);
    }
    if (result.data === null || result.data === undefined) {
      throw new Error("DRL " + this.mode + " " + operation +
        " persistence returned no result");
    }
    return result.data as T;
  }
}

export class ClassicDrlPersistenceAdapter extends ModePersistenceAdapter {
  protected readonly mode = "classic" as const;
  protected readonly rpcNames = {
    market: "dfm_classic_persist_market_snapshot",
    awards: "dfm_classic_persist_award_bundle",
    newsroom: "dfm_classic_persist_news_article",
    ladder: "dfm_classic_persist_ladder_result",
    appendMovement: "dfm_classic_append_price_movement",
    listMovements: "dfm_classic_list_market_movements",
    listAwards: "dfm_classic_list_awards",
    listCredits: "dfm_classic_list_coach_credits",
    listNews: "dfm_classic_list_news_articles",
    listLadder: "dfm_classic_list_ladder_results"
  };
}

export class DraftDrlPersistenceAdapter extends ModePersistenceAdapter {
  protected readonly mode = "draft" as const;
  protected readonly rpcNames = {
    market: "dfm_draft_persist_market_snapshot",
    awards: "dfm_draft_persist_award_bundle",
    newsroom: "dfm_draft_persist_news_article",
    ladder: "dfm_draft_persist_ladder_result",
    appendMovement: "dfm_draft_append_price_movement",
    listMovements: "dfm_draft_list_market_movements",
    listAwards: "dfm_draft_list_awards",
    listCredits: "dfm_draft_list_coach_credits",
    listNews: "dfm_draft_list_news_articles",
    listLadder: "dfm_draft_list_ladder_results"
  };
}
