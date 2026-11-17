from pydantic import BaseModel, Field
from typing import List, Optional

class NewsArticleCreate(BaseModel):
    sport_code: str = Field(..., description="Sport code e.g. DRL")
    league_type: str = Field(..., description="nrl_fantasy, super_league_fantasy, or h2h_league")
    league_id: Optional[str] = Field(None, description="UUID of the H2H league if applicable")
    category: str = Field(..., description="team_list, injury, h2h_preview, h2h_review, trade_alert, finals_race")
    title: str
    summary: str
    content: str
    related_franchise_ids: Optional[List[str]] = []

class H2HPreviewRequest(BaseModel):
    home_franchise_name: str
    away_franchise_name: str
    home_projected_score: float
    away_projected_score: float
    round_number: int
