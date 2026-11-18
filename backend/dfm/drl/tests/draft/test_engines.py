import unittest
from backend.dfm.drl.draft.core.odds_engine.engine import OddsEngine
from backend.dfm.drl.draft.core.odds_engine.models import MarketType,MarketSource
from backend.dfm.drl.draft.core.awards_engine.engine import AwardsEngine
from backend.dfm.drl.draft.core.awards_engine.models import PlayerCandidate,FixtureInput,AwardCategory
from backend.dfm.drl.draft.core.newsroom.engine import NewsroomEngine
from backend.dfm.drl.draft.core.ladder_engine.engine import LadderEngine
from backend.dfm.drl.draft.core.ladder_engine.models import MatchResult
class MemoryNews:
    def __init__(self):self.items=[]
    def append_once(self,a):
        if any(x.article_id==a.article_id for x in self.items):return False
        self.items.append(a);return True
    def list_articles(self,league_id,limit=25):return tuple(a for a in self.items if a.league_id==league_id)[:limit]
class DraftEngineTests(unittest.TestCase):
    def setUp(self):self.source=MarketSource("verified-input","official_stats",True,"Verified fantasy competition data")
    def test_h2h_odds_are_mode_owned_and_normalised(self):
        result=OddsEngine().calculate_head_to_head(market_id="match-1",home_id="h",home_name="Home",home_projection=100,away_id="a",away_name="Away",away_projection=80,source=self.source)
        self.assertEqual(result.mode,"draft");self.assertAlmostEqual(sum(o.probability for o in result.outcomes),1.0);self.assertGreater(result.outcomes[0].probability,result.outcomes[1].probability)
    def test_mode_market_boundary(self):
        result=OddsEngine().calculate_ranked_market(market_type=MarketType.TEAM_OF_THE_WEEK,market_id="totw",projections={"p1":90,"p2":80},labels={"p1":"One","p2":"Two"},source=self.source);self.assertEqual(result.market_type,MarketType.TEAM_OF_THE_WEEK)
    def test_round_gating_and_expected_motr_motm_count(self):
        positions=["WFB","WFB","WFB","CTR","CTR","HLF","HLF","EDG","EDG","MID","MID","MID","HOK","HOK"];fixtures=[]
        for i in range(7):
            a=PlayerCandidate(f"p{i}a",f"Player {i}A",100-i,f"f{i}a",f"c{i}a",primary_position=positions[i*2])
            b=PlayerCandidate(f"p{i}b",f"Player {i}B",80-i,f"f{i}b",f"c{i}b",primary_position=positions[i*2+1])
            fixtures.append(FixtureInput(f"fixture-{i}",True,True,(a,b),{a.franchise_id:150,b.franchise_id:130}))
        fixtures[0]=FixtureInput("fixture-0",False,True,fixtures[0].candidates,fixtures[0].franchise_totals)
        with self.assertRaises(RuntimeError):AwardsEngine().finalise_round(1,tuple(fixtures))
        fixtures[0]=FixtureInput("fixture-0",True,True,fixtures[0].candidates,fixtures[0].franchise_totals)
        awards=AwardsEngine().finalise_round(1,tuple(fixtures))
        self.assertEqual(sum(a.category is AwardCategory.MOTR for a in awards),1)
        self.assertEqual(sum(a.category is AwardCategory.MOTM for a in awards),6)
        self.assertEqual(sum(a.category is AwardCategory.TOTW for a in awards),13)
    def test_round_awards_cannot_publish_early(self):
        engine=NewsroomEngine(MemoryNews())
        with self.assertRaises(RuntimeError):engine.publish_round_awards(article_id="a1",league_id="l1",round_number=1,awards_finalised=False,title="Awards",summary="Pending",award_report="")
        article=engine.publish_round_awards(article_id="a1",league_id="l1",round_number=1,awards_finalised=True,title="Awards",summary="Final",award_report="Final results")
        self.assertEqual(article.mode,"draft")
    def test_ladder_uses_supplied_competition_points_and_pf_pa(self):
        rows=LadderEngine().competition_ladder(("home","away"),(MatchResult("home","away",100,80,2,0),))
        self.assertEqual(rows[0].franchise_id,"home");self.assertEqual(rows[0].points_differential,20);self.assertEqual(rows[0].played,1)
    def test_draft_totw_positional_xiii_excludes_non_contributing_bench(self):
        engine=AwardsEngine();candidates=[]
        for pos,count in (("WFB",3),("CTR",2),("HLF",2),("EDG",2),("MID",3),("HOK",1)):
            for i in range(count):candidates.append(PlayerCandidate(f"{pos}{i}",f"{pos} Player {i}",90-i,f"f{pos}{i}",f"c{pos}{i}",primary_position=pos))
        candidates.append(PlayerCandidate("bench","Bench",999,"bench-f","bench-c",primary_position="WFB",score_contributed=False))
        selected=engine.select_positional_team(candidates,{})
        self.assertEqual(sum(len(v) for v in selected.values()),13)
        self.assertNotIn("bench",{c.player_id for group in selected.values() for c in group})
if __name__=="__main__":unittest.main()
