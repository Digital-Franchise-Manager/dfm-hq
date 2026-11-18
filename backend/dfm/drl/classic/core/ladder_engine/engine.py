"""CLASSIC competition, player-awards and coach-awards ladders."""
from collections import defaultdict
from typing import Iterable
from .models import MatchResult,Standing,AwardStanding
class LadderEngine:
    mode="classic"
    def competition_ladder(self,franchise_ids:Iterable[str],matches:Iterable[MatchResult])->tuple[Standing,...]:
        stats={fid:{"played":0,"wins":0,"losses":0,"draws":0,"cp":0,"pf":0.0,"pa":0.0} for fid in franchise_ids}
        for m in matches:
            if not m.finalised:continue
            if m.home_franchise_id not in stats or m.away_franchise_id not in stats:raise ValueError("match contains franchise outside this mode's competition")
            h=stats[m.home_franchise_id];a=stats[m.away_franchise_id];h["played"]+=1;a["played"]+=1;h["pf"]+=m.home_score;h["pa"]+=m.away_score;a["pf"]+=m.away_score;a["pa"]+=m.home_score;h["cp"]+=m.home_competition_points;a["cp"]+=m.away_competition_points
            if m.home_score>m.away_score:h["wins"]+=1;a["losses"]+=1
            elif m.home_score<m.away_score:a["wins"]+=1;h["losses"]+=1
            else:h["draws"]+=1;a["draws"]+=1
        ordered=sorted(stats.items(),key=lambda x:(x[1]["cp"],x[1]["pf"]-x[1]["pa"],x[1]["pf"],x[0]),reverse=True)
        return tuple(Standing(fid,s["played"],s["wins"],s["losses"],s["draws"],s["cp"],s["pf"],s["pa"],s["pf"]-s["pa"],i+1) for i,(fid,s) in enumerate(ordered))
    @staticmethod
    def player_awards_ladder(records,position_by_player:dict[str,str]|None=None,position_filter:str="ALL")->tuple[AwardStanding,...]:
        events={}
        for r in records:
            key=(r.round_number,r.category,r.player_id)
            events[key]=max(events.get(key,0),r.points)
        totals=defaultdict(lambda:defaultdict(int))
        for (_,category,pid),points in events.items():totals[pid][category.value]+=points
        rows=[]
        for pid,columns in totals.items():
            pos=(position_by_player or {}).get(pid)
            if position_filter!="ALL" and pos!=position_filter:continue
            rows.append((pid,dict(columns),sum(columns.values()),pos))
        rows.sort(key=lambda x:(x[2],x[0]),reverse=True)
        return tuple(AwardStanding(pid,cols,total,i+1,pos) for i,(pid,cols,total,pos) in enumerate(rows))
    @staticmethod
    def coach_awards_ladder(credits)->tuple[AwardStanding,...]:
        totals=defaultdict(lambda:defaultdict(int))
        for c in credits:totals[c.coach_id][c.category.value]+=c.points
        rows=[(cid,dict(cols),sum(cols.values())) for cid,cols in totals.items()];rows.sort(key=lambda x:(x[2],x[0]),reverse=True)
        return tuple(AwardStanding(cid,cols,total,i+1) for i,(cid,cols,total) in enumerate(rows))
