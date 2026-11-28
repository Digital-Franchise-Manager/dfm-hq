"""Independent draft odds domain records."""
from dataclasses import dataclass
from enum import Enum
class MarketType(str,Enum):
    HEAD_TO_HEAD="head_to_head"
    PREMIERSHIP="premiership"
    FINALS_QUALIFICATION="finals_qualification"
    GRAND_FINAL_QUALIFICATION="grand_final_qualification"
    PLAY_OF_THE_WEEK="play_of_the_week"
    MAN_OF_THE_MATCH="man_of_the_match"
    MAN_OF_THE_ROUND="man_of_the_round"
    PLAYER_OF_THE_YEAR="player_of_the_year"
    COACH_OF_THE_YEAR="coach_of_the_year"
    TEAM_OF_THE_WEEK="team_of_the_week"
    TEAM_OF_THE_YEAR="team_of_the_year"
@dataclass(frozen=True,slots=True)
class MarketSource:
    source_id:str
    category:str
    verified:bool
    summary:str
    def __post_init__(self):
        if not all(v.strip() for v in (self.source_id,self.category,self.summary)):raise ValueError("source metadata must not be blank")
@dataclass(frozen=True,slots=True)
class MarketOutcome:
    selection_id:str
    label:str
    probability:float
    decimal_price:float
@dataclass(frozen=True,slots=True)
class MarketCalculation:
    mode:str
    market_type:MarketType
    market_id:str
    outcomes:tuple[MarketOutcome,...]
    source:MarketSource
    model_version:str
    official:bool
    def __post_init__(self):
        if self.mode!="draft":raise ValueError("market mode does not match this engine")
        if not self.market_id.strip() or not self.model_version.strip() or len(self.outcomes)<2:raise ValueError("market identity and two outcomes are required")
        if any(not 0<o.probability<1 for o in self.outcomes):raise ValueError("probabilities must be between zero and one")
        if abs(sum(o.probability for o in self.outcomes)-1)>1e-8:raise ValueError("probabilities must sum to one")
        if self.official!=self.source.verified:raise ValueError("official status must match verified source")
@dataclass(frozen=True,slots=True)
class PriceMovement:
    market_id:str
    selection_id:str
    revision:int
    previous_probability:float
    revised_probability:float
    previous_price:float
    revised_price:float
    source_id:str
    model_version:str
    idempotency_key:str
