"""draft competition and award ladder value objects."""
from dataclasses import dataclass
@dataclass(frozen=True,slots=True)
class MatchResult:
    home_franchise_id:str
    away_franchise_id:str
    home_score:float
    away_score:float
    home_competition_points:int
    away_competition_points:int
    finalised:bool=True
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
