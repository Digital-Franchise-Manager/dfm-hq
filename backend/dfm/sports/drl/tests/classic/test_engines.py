import unittest
from backend.dfm.sports.drl.classic.core.odds_engine.engine import OddsEngine
from backend.dfm.sports.drl.classic.core.odds_engine.models import MarketType,MarketSource
from backend.dfm.sports.drl.classic.core.awards_engine.engine import AwardsEngine
from backend.dfm.sports.drl.classic.core.awards_engine.models import PlayerCandidate,FixtureInput,AwardCategory
from backend.dfm.sports.drl.classic.core.newsroom.engine import NewsroomEngine
from backend.dfm.sports.drl.classic.core.ladder_engine.engine import LadderEngine
from backend.dfm.sports.drl.classic.core.ladder_engine.models import MatchResult
class MemoryNews:
    def __init__(self):self.items=[]
    def append_once(self,a):
        if any(x.article_id==a.article_id for x in self.items):return False
        self.items.append(a);return True
    def list_articles(self,league_id,limit=25):return tuple(a for a in self.items if a.league_id==league_id)[:limit]
class ClassicEngineTests(unittest.TestCase):
    def setUp(self):self.source=MarketSource("verified-input","official_stats",True,"Verified fantasy competition data")
    def test_h2h_odds_are_mode_owned_and_normalised(self):
        result=OddsEngine().calculate_head_to_head(market_id="match-1",home_id="h",home_name="Home",home_projection=100,away_id="a",away_name="Away",away_projection=80,source=self.source)
        self.assertEqual(result.mode,"classic");self.assertAlmostEqual(sum(o.probability for o in result.outcomes),1.0);self.assertGreater(result.outcomes[0].probability,result.outcomes[1].probability)
    def test_mode_market_boundary(self):
        self.assertFalse(hasattr(MarketType,"TEAM_OF_THE_WEEK"))
    def test_round_gating_and_expected_motr_motm_count(self):
        fixtures=[]
        for i in range(7):
            a=PlayerCandidate(f"p{i}a",f"Player {i}A",100-i,f"f{i}a",f"c{i}a",primary_position="WFB")
            b=PlayerCandidate(f"p{i}b",f"Player {i}B",80-i,f"f{i}b",f"c{i}b",primary_position="CTR")
            fixtures.append(FixtureInput(f"fixture-{i}",True,True,(a,b),{a.franchise_id:150,b.franchise_id:130}))
        fixtures[0]=FixtureInput("fixture-0",False,True,fixtures[0].candidates,fixtures[0].franchise_totals)
        with self.assertRaises(RuntimeError):AwardsEngine().finalise_round(1,tuple(fixtures))
        fixtures[0]=FixtureInput("fixture-0",True,True,fixtures[0].candidates,fixtures[0].franchise_totals)
        awards=AwardsEngine().finalise_round(1,tuple(fixtures))
        self.assertEqual(sum(a.category is AwardCategory.MOTR for a in awards),1)
        self.assertEqual(sum(a.category is AwardCategory.MOTM for a in awards),6)
    def test_round_awards_cannot_publish_early(self):
        engine=NewsroomEngine(MemoryNews())
        with self.assertRaises(RuntimeError):engine.publish_round_awards(article_id="a1",league_id="l1",round_number=1,awards_finalised=False,title="Awards",summary="Pending",award_report="")
        article=engine.publish_round_awards(article_id="a1",league_id="l1",round_number=1,awards_finalised=True,title="Awards",summary="Final",award_report="Final results")
        self.assertEqual(article.mode,"classic")
    def test_ladder_uses_supplied_competition_points_and_pf_pa(self):
        rows=LadderEngine().competition_ladder(("home","away"),(MatchResult("home","away",100,80,2,0),))
        self.assertEqual(rows[0].franchise_id,"home");self.assertEqual(rows[0].points_differential,20);self.assertEqual(rows[0].played,1)
    def test_classic_shared_player_owner_uses_full_team_total(self):
        engine=AwardsEngine();low=PlayerCandidate("shared","Shared Player",100,"low","old-coach");high=PlayerCandidate("shared","Shared Player",100,"high","new-coach")
        fixture=FixtureInput("one",True,True,(low,high,PlayerCandidate("other","Other",80,"other","other-coach")),{ "low":120,"high":150,"other":100})
        awards=engine.finalise_round(1,(fixture,));motr=[a for a in awards if a.category is AwardCategory.MOTR]
        self.assertEqual([a.coach_id for a in motr],["new-coach"])
if __name__=="__main__":unittest.main()
