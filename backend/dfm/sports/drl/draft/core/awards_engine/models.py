"""draft award records with immutable ownership at award time."""
from dataclasses import dataclass
from enum import Enum
from typing import Mapping
from backend.dfm.sports.drl.core.player_positions import validate_player_positions
class AwardCategory(str,Enum):
    MOTM="man_of_the_match"
    MOTR="man_of_the_round"
    PLAY_OF_THE_WEEK="play_of_the_week"
    TOTW="team_of_the_week"
    TOTY="team_of_the_year"
    POTY="player_of_the_year"
    COTY="coach_of_the_year"
@dataclass(frozen=True,slots=True)
class PlayerCandidate:
    player_id:str
    player_name:str
    base_score:float
    franchise_id:str
    coach_id:str
    primary_position:str=""
    secondary_positions:tuple[str,...]=()
    score_contributed:bool=True
    nrl_team_points:int=0
    def __post_init__(self):
        if not all(v.strip() for v in (self.player_id,self.player_name,self.franchise_id,self.coach_id)) or not self.base_score>=0:raise ValueError("candidate identifiers and score must be valid")
        validate_player_positions(self.primary_position, self.secondary_positions)
@dataclass(frozen=True,slots=True)
class FixtureInput:
    fixture_id:str
    completed:bool
    stats_verified:bool
    candidates:tuple[PlayerCandidate,...]
    franchise_totals:Mapping[str,float]
@dataclass(frozen=True,slots=True)
class AwardRecord:
    award_id:str
    category:AwardCategory
    round_number:int
    player_id:str
    player_name:str
    franchise_id:str
    coach_id:str
    base_score:float
    points:int
    position:str|None=None
    achievement_only:bool=False
@dataclass(frozen=True,slots=True)
class CoachCredit:
    coach_id:str
    franchise_id:str
    player_id:str
    category:AwardCategory
    round_number:int
    points:int
