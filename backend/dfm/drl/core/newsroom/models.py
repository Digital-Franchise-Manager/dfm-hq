from pydantic import BaseModel, Field
from typing import List, Optional, Dict

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

class FranchiseBrandingPayload(BaseModel):
    franchise_id: str
    primary_name: str
    secondary_name: str
    abbreviated_name: str
    coach_name: str
    primary_logo_url: Optional[str] = None
    wordmark_logo_url: Optional[str] = None
    simplified_logo_url: Optional[str] = None
    primary_color: str = "#0F172A"
    secondary_color: str = "#FFFFFF"
    accent_color: Optional[str] = "#BFFF00"
    recent_form: List[str] = []

class MatchPlayerSlot(BaseModel):
    slot_number: int
    is_starting: bool
    player_id: str
    player_name: str
    player_photo_url: Optional[str] = None
    position: str
    leadership: Optional[str] = None
    availability: str = "available"
    live_score: float = 0.0
    projected_score: float = 0.0

class MatchCentreResponse(BaseModel):
    match_id: str
    league_id: str
    round_number: int
    status: str
    home_team: FranchiseBrandingPayload
    away_team: FranchiseBrandingPayload
    home_score: float
    away_score: float
    home_projected: float
    away_projected: float
    home_lineup: List[MatchPlayerSlot]
    away_lineup: List[MatchPlayerSlot]
    ai_article: Optional[Dict[str, str]] = None
