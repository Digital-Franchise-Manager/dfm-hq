"""Draft competition and award ladder value objects."""
from dataclasses import dataclass
import math
@dataclass(frozen=True,slots=True)
class MatchResult:
    home_franchise_id:str
    away_franchise_id:str
    home_score:float
    away_score:float
    home_competition_points:int
    away_competition_points:int
    finalised:bool=True
    def __post_init__(self):
        if not self.home_franchise_id.strip() or not self.away_franchise_id.strip() or self.home_franchise_id==self.away_franchise_id:raise ValueError("match requires two distinct franchise IDs")
        if not all(math.isfinite(x) and x>=0 for x in (self.home_score,self.away_score)):raise ValueError("fantasy scores must be finite and non-negative")
        if self.home_competition_points<0 or self.away_competition_points<0:raise ValueError("competition points cannot be negative")
@dataclass(frozen=True,slots=True)
class Standing:
    franchise_id:str
    played:int
    wins:int
    losses:int
    draws:int
    competition_points:int
    points_for:float
    points_against:float
    points_differential:float
    position:int
@dataclass(frozen=True,slots=True)
class AwardStanding:
    entity_id:str
    award_columns:dict[str,int]
    total_points:int
    position:int
    primary_position:str|None=None
