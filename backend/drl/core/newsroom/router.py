from fastapi import APIRouter, HTTPException
from backend.dfm.drl.core.newsroom.models import H2HPreviewRequest
from backend.dfm.drl.core.newsroom.service import NewsroomAIService

router = APIRouter(prefix="/api/dfm/drl/newsroom", tags=["Newsroom"])

@router.get("/feed/{league_id}")
async def get_league_news_feed(league_id: str):
    """
    Fetches news feed items and H2H chronicles for a specific league.
    """
    # Database retrieval logic using Supabase goes here
    return {"status": "success", "league_id": league_id, "articles": []}

@router.post("/generate/h2h-preview")
async def trigger_h2h_preview_generation(payload: H2HPreviewRequest):
    """
    Triggers Gemini AI to write and return a broadcast-style pre-game H2H analysis article.
    """
    try:
        article_data = await NewsroomAIService.generate_h2h_matchup_article(
            home_franchise=payload.home_franchise_name,
            away_franchise=payload.away_franchise_name,
            home_projected_score=payload.home_projected_score,
            away_projected_score=payload.away_projected_score,
            round_number=payload.round_number
        )
        return {
            "message": "AI broadcast-style H2H match preview generated successfully",
            "article": article_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
