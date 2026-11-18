"""Mode-isolated newsroom article records."""
from dataclasses import dataclass
from enum import Enum
class NewsCategory(str,Enum):
    PREVIEW="preview"
    MATCH_REPORT="match_report"
    ROUND_AWARDS="round_awards"
    ODDS_UPDATE="odds_update"
    INJURY="injury"
    TRANSFER="transfer"
    FINALS_RACE="finals_race"
@dataclass(frozen=True,slots=True)
class NewsArticle:
    article_id:str
    mode:str
    league_id:str
    round_number:int
    category:NewsCategory
    title:str
    summary:str
    content:str
    published:bool=True
    def __post_init__(self):
        if self.mode!="classic":raise ValueError("article belongs to another competition mode")
        if not all(v.strip() for v in (self.article_id,self.league_id,self.title,self.summary,self.content)):raise ValueError("article identity and content are required")
