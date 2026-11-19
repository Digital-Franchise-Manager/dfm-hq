"""DRAFT award selection, round finalisation and coach ownership credits."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import replace
from typing import Iterable,Mapping
from .models import AwardCategory,PlayerCandidate,FixtureInput,AwardRecord,CoachCredit
from backend.dfm.drl.core.player_positions import POSITIONAL_XIII as POSITIONS
POINTS={AwardCategory.MOTM:2,AwardCategory.MOTR:3,AwardCategory.TOTW:1,}
class AwardsEngine:
    mode="draft"
    def _best(self,candidates:Iterable[PlayerCandidate],totals:Mapping[str,float],require_one_player:bool=False)->list[PlayerCandidate]:
        pool=list(candidates)
        if not pool:return []
        score=max(c.base_score for c in pool);tied=[c for c in pool if c.base_score==score];groups=defaultdict(list)
        for c in tied:groups[c.player_id].append(c)
        if require_one_player and len(groups)>1:raise RuntimeError("distinct players are tied for the single MOTR award; explicit competition tie resolution is required")
        winners=[]
        for owners in groups.values():
            if self.mode=="classic" and len(owners)>1:
                best=max(totals.get(c.franchise_id,float("-inf")) for c in owners)
                winners.extend(c for c in owners if totals.get(c.franchise_id,float("-inf"))==best)
            else:winners.extend(owners)
        return winners
    @staticmethod
    def _record(category,round_no,c,points,position=None):
        return AwardRecord(f"draft:{round_no}:{category.value}:{c.player_id}:{c.franchise_id}",category,round_no,c.player_id,c.player_name,c.franchise_id,c.coach_id,c.base_score,points,position,points==0)
    def finalise_round(self,round_number:int,fixtures:tuple[FixtureInput,...])->tuple[AwardRecord,...]:
        if round_number<1 or not fixtures or len({f.fixture_id for f in fixtures})!=len(fixtures):raise ValueError("valid round and unique fixtures required")
        if any(not f.completed or not f.stats_verified for f in fixtures):raise RuntimeError("round stays open until every assigned fixture is complete and verified")
        candidates=[c for f in fixtures for c in f.candidates]
        if not candidates:raise ValueError("verified player statistics are required")
        round_totals=defaultdict(float)
        for f in fixtures:
            for fid,score in f.franchise_totals.items():round_totals[fid]+=score
        motr=self._best(candidates,round_totals,True)
        if not motr:raise ValueError("no eligible MOTR candidate")
        records=[self._record(AwardCategory.MOTR,round_number,c,POINTS[AwardCategory.MOTR]) for c in motr];motr_ids={c.player_id for c in motr}
        # The MOTR fixture has no separate MOTM: 7 fixtures yield 1 MOTR + 6 MOTM.
        for fixture in fixtures:
            if any(c.player_id in motr_ids for c in fixture.candidates):continue
            winners=self._best(fixture.candidates,fixture.franchise_totals)
            if not winners:raise ValueError(f"fixture {fixture.fixture_id} has no eligible MOTM candidate")
            records.extend(self._record(AwardCategory.MOTM,round_number,c,POINTS[AwardCategory.MOTM]) for c in winners)
        records.extend(self._team_of_week(round_number,candidates,round_totals))
        highest={}
        for a in records:highest[a.player_id]=max(highest.get(a.player_id,0),a.points)
        winning_category={}
        for a in records:
            if a.points==highest[a.player_id] and a.points>0:winning_category.setdefault(a.player_id,a.category)
        return tuple(replace(a,points=(a.points if a.category==winning_category.get(a.player_id) else 0),achievement_only=(a.category!=winning_category.get(a.player_id) or a.points==0)) for a in records)
    def coach_credits(self,awards:Iterable[AwardRecord])->tuple[CoachCredit,...]:
        return tuple(CoachCredit(a.coach_id,a.franchise_id,a.player_id,a.category,a.round_number,a.points) for a in awards if a.points>0)
    def player_points(self,awards:Iterable[AwardRecord])->dict[str,int]:
        # A Classic shared-owner tie creates multiple coach records but only one
        # individual player award event. Deduplicate that event before summing.
        events={}
        for a in awards:
            key=(a.round_number,a.category,a.player_id)
            events[key]=max(events.get(key,0),a.points)
        totals=defaultdict(int)
        for (_,_,pid),points in events.items():totals[pid]+=points
        return dict(totals)
    def coach_points(self,credits:Iterable[CoachCredit])->dict[str,int]:
        totals=defaultdict(int)
        for c in credits:totals[c.coach_id]+=c.points
        return dict(totals)
    def select_player_of_year(self,awards:Iterable[AwardRecord])->tuple[str,...]:
        totals=self.player_points(awards)
        if not totals:return ()
        best=max(totals.values());return tuple(sorted(pid for pid,points in totals.items() if points==best))
    def select_coach_of_year(self,credits:Iterable[CoachCredit])->tuple[str,...]:
        totals=self.coach_points(credits)
        if not totals:return ()
        best=max(totals.values());return tuple(sorted(cid for cid,points in totals.items() if points==best))
    def record_play_of_the_week(self,round_number:int,candidate:PlayerCandidate)->AwardRecord:
        return self._record(AwardCategory.PLAY_OF_THE_WEEK,round_number,candidate,0)
    def _team_of_week(self,round_no,candidates,franchise_totals):
        selected=self.select_positional_team(candidates,franchise_totals,require_contribution=True)
        missing={pos:slots-len(selected[pos]) for pos,slots in POSITIONS if len(selected[pos])<slots}
        if missing:raise RuntimeError(f"cannot finalise Team of the Week; missing eligible positions: {missing}")
        return [self._record(AwardCategory.TOTW,round_no,c,POINTS[AwardCategory.TOTW],pos) for pos,group in selected.items() for c in group]
    def select_positional_team(self,candidates:Iterable[PlayerCandidate],franchise_totals:Mapping[str,float],require_contribution:bool=True):
        pool=[c for c in candidates if c.score_contributed or not require_contribution];used=set();result={p:[] for p,_ in POSITIONS}
        for pos,slots in POSITIONS:
            group=[c for c in pool if c.primary_position==pos and c.player_id not in used]
            picks=self._rank(group,slots,franchise_totals);result[pos].extend(picks);used.update(c.player_id for c in picks)
        for pos,slots in POSITIONS:
            left=slots-len(result[pos])
            if left>0:
                group=[c for c in pool if pos in c.secondary_positions and c.primary_position!=pos and c.player_id not in used]
                picks=self._rank(group,left,franchise_totals);result[pos].extend(picks);used.update(c.player_id for c in picks)
        return {k:tuple(v) for k,v in result.items()}
    @staticmethod
    def _rank(candidates,slots,franchise_totals):
        if slots<=0 or not candidates:return []
        ordered=sorted(candidates,key=lambda c:(c.base_score,franchise_totals.get(c.franchise_id,0),c.nrl_team_points),reverse=True)
        if len(ordered)<=slots:return ordered
        cutoff=ordered[slots-1];key=(cutoff.base_score,franchise_totals.get(cutoff.franchise_id,0),cutoff.nrl_team_points)
        return [c for c in ordered if (c.base_score,franchise_totals.get(c.franchise_id,0),c.nrl_team_points)>=key]
    def select_team_of_year(self,candidates,franchise_season_totals):
        # base_score is cumulative player-award points; TOTY is not gated by a weekly score contribution.
        return self.select_positional_team(candidates,franchise_season_totals,require_contribution=False)

