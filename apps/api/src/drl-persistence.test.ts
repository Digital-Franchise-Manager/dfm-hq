import { describe, expect, it, vi } from "vitest";
import {
  ClassicDrlPersistenceAdapter,
  DraftDrlPersistenceAdapter,
  type DfmRpcExecutor
} from "./drl-persistence.js";

function createRpc(data: unknown = true) {
  const rpc = vi.fn<DfmRpcExecutor>().mockResolvedValue({ data, error: null });
  return rpc;
}

const market = {
  leagueId: "league-1",
  marketId: "market-1",
  marketType: "head_to_head",
  revision: 1,
  source: {
    sourceId: "source-1",
    category: "official",
    verified: true,
    summary: "Verified fixture data"
  },
  modelVersion: "0.2.0",
  official: true,
  outcomes: [
    { selectionId: "home", label: "Home", probability: 0.55, decimalPrice: 1.8182 },
    { selectionId: "away", label: "Away", probability: 0.45, decimalPrice: 2.2222 }
  ]
};

describe("mode-isolated DRL persistence adapters", () => {
  it("routes Classic market writes only to the Classic RPC", async () => {
    const rpc = createRpc("snapshot-id");
    const adapter = new ClassicDrlPersistenceAdapter(rpc);
    await adapter.persistMarketSnapshot(market);
    expect(rpc).toHaveBeenCalledWith(
      "dfm_classic_persist_market_snapshot",
      expect.objectContaining({ p_league_id: "league-1", p_revision: 1 })
    );
  });

  it("routes Draft market writes only to the Draft RPC", async () => {
    const rpc = createRpc("snapshot-id");
    const adapter = new DraftDrlPersistenceAdapter(rpc);
    await adapter.persistMarketSnapshot(market);
    expect(rpc).toHaveBeenCalledWith(
      "dfm_draft_persist_market_snapshot",
      expect.any(Object)
    );
  });

  it("rejects malformed probabilities before making an RPC call", async () => {
    const rpc = createRpc("snapshot-id");
    const adapter = new ClassicDrlPersistenceAdapter(rpc);
    await expect(adapter.persistMarketSnapshot({
      ...market,
      outcomes: [
        { ...market.outcomes[0], probability: 0.7 },
        { ...market.outcomes[1], probability: 0.45 }
      ]
    })).rejects.toThrow("must sum to one");
    expect(rpc).not.toHaveBeenCalled();
  });

  it("commits awards and award-time coach credits through one RPC", async () => {
    const rpc = createRpc(1);
    const adapter = new ClassicDrlPersistenceAdapter(rpc);
    await adapter.persistAwardBundle("league-1", [{
      awardId: "award-1",
      category: "man_of_the_match",
      roundNumber: 1,
      playerId: "player-1",
      playerName: "Player One",
      franchiseId: "00000000-0000-0000-0000-000000000001",
      coachId: "coach-at-award-time",
      baseScore: 88,
      points: 2
    }], [{
      coachId: "coach-at-award-time",
      franchiseId: "00000000-0000-0000-0000-000000000001",
      playerId: "player-1",
      category: "man_of_the_match",
      roundNumber: 1,
      points: 2
    }]);
    expect(rpc).toHaveBeenCalledTimes(1);
    expect(rpc.mock.calls[0][0]).toBe("dfm_classic_persist_award_bundle");
  });

  it("rejects non-finalised ladder results", async () => {
    const rpc = createRpc(true);
    const adapter = new DraftDrlPersistenceAdapter(rpc);
    await expect(adapter.persistFinalisedMatch({
      leagueId: "league-1",
      fixtureId: "fixture-1",
      homeFranchiseId: "00000000-0000-0000-0000-000000000001",
      awayFranchiseId: "00000000-0000-0000-0000-000000000002",
      homeScore: 10,
      awayScore: 8,
      homeCompetitionPoints: 2,
      awayCompetitionPoints: 0,
      finalised: false
    })).rejects.toThrow("only finalised");
    expect(rpc).not.toHaveBeenCalled();
  });


  it("routes append-only market history to the mode-specific RPC", async () => {
    const rpc = createRpc(true);
    const adapter = new DraftDrlPersistenceAdapter(rpc);
    await adapter.appendPriceMovement("league-1", {
      marketId: "market-1",
      selectionId: "home",
      revision: 2,
      previousProbability: 0.55,
      revisedProbability: 0.60,
      previousPrice: 1.8182,
      revisedPrice: 1.6667,
      sourceId: "source-2",
      modelVersion: "0.2.0",
      idempotencyKey: "movement-2"
    });
    expect(rpc).toHaveBeenCalledWith(
      "dfm_draft_append_price_movement",
      expect.objectContaining({ p_market_id: "market-1", p_revision: 2 })
    );
  });

  it("maps persisted newsroom rows into engine article records", async () => {
    const rpc = createRpc([{
      article_id: "article-1",
      league_id: "league-1",
      round_number: 2,
      category: "match_report",
      title: "Round report",
      summary: "Summary",
      content: "Body",
      published: true
    }]);
    const adapter = new ClassicDrlPersistenceAdapter(rpc);
    const articles = await adapter.listNewsArticles("league-1", 10);
    expect(articles).toHaveLength(1);
    expect(articles[0]).toMatchObject({
      articleId: "article-1",
      leagueId: "league-1",
      category: "match_report"
    });
    expect(rpc).toHaveBeenCalledWith(
      "dfm_classic_list_news_articles",
      { p_league_id: "league-1", p_limit: 10 }
    );
  });

  it("maps persisted ladder results without recalculating engine points", async () => {
    const rpc = createRpc([{
      fixture_id: "fixture-1",
      home_franchise_id: "home-franchise",
      away_franchise_id: "away-franchise",
      home_score: 44.5,
      away_score: 39,
      home_competition_points: 2,
      away_competition_points: 0,
      finalised: true
    }]);
    const adapter = new DraftDrlPersistenceAdapter(rpc);
    const results = await adapter.listFinalisedMatches("league-1");
    expect(results[0]).toMatchObject({
      fixtureId: "fixture-1",
      homeCompetitionPoints: 2,
      awayCompetitionPoints: 0,
      finalised: true
    });
  });

  it("propagates server-side RPC errors without swallowing them", async () => {
    const rpc = vi.fn<DfmRpcExecutor>().mockResolvedValue({
      data: null,
      error: { message: "permission denied" }
    });
    const adapter = new DraftDrlPersistenceAdapter(rpc);
    await expect(adapter.appendNewsArticle({
      articleId: "article-1",
      leagueId: "league-1",
      roundNumber: 1,
      category: "preview",
      title: "Preview",
      summary: "Summary",
      content: "Body"
    })).rejects.toThrow("permission denied");
  });
});
