from fastapi import APIRouter, HTTPException, Depends
from backend.dfm.drl.core.newsroom.models import (
    H2HPreviewRequest,
    MatchCentreResponse,
    FranchiseBrandingPayload,
    MatchPlayerSlot,
)
from backend.dfm.drl.core.newsroom.service import NewsroomAIService
from backend.dfm.drl.core.database import get_supabase_client

router = APIRouter(prefix="/api/dfm/drl/newsroom", tags=["Newsroom"])


@router.get("/feed/{league_id}")
async def get_league_news_feed(league_id: str, supabase=Depends(get_supabase_client)):
    """
    Fetches news feed items and H2H chronicles for a specific league.
    """
    res = (
        supabase.table("newsroom_articles")
        .select("*")
        .eq("league_id", league_id)
        .order("created_at", desc=True)
        .limit(25)
        .execute()
    )
    return {"status": "success", "league_id": league_id, "articles": res.data or []}


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
            round_number=payload.round_number,
        )
        return {
            "message": "AI broadcast-style H2H match preview generated successfully",
            "article": article_data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _format_lineup_slots(raw_slots: list) -> list[MatchPlayerSlot]:
    """
    Sorts squad slots 1-17 and enforces the global DRL rule:
    Starting 13 (slots 1-13) cannot carry an 'emergency' badge.
    """
    sorted_slots = sorted(raw_slots, key=lambda x: x.get("slot_number", 99))
    formatted = []

    for row in sorted_slots:
        slot_num = row["slot_number"]
        is_starting = slot_num <= 13
        player_meta = row.get("players") or {}

        availability = row.get("availability_status", "available")
        if is_starting and availability == "emergency":
            availability = "available"

        formatted.append(
            MatchPlayerSlot(
                slot_number=slot_num,
                is_starting=is_starting,
                player_id=row["player_id"],
                player_name=player_meta.get("full_name", "Unknown Player"),
                player_photo_url=player_meta.get("headshot_url"),
                position=row.get("assigned_position") or player_meta.get("primary_position", "INT"),
                leadership=row.get("leadership_role"),
                availability=availability,
                live_score=float(row.get("live_score", 0.0)),
                projected_score=float(row.get("projected_score", 0.0)),
            )
        )
    return formatted


@router.get("/match-centre/{match_id}", response_model=MatchCentreResponse)
async def get_full_match_centre(match_id: str, supabase=Depends(get_supabase_client)):
    """
    Aggregates the match scoreflow, Team A (Home) & Team B (Away) public profiles,
    exact coach names, franchise hex color palettes, ordered 1-17 lineups, and
    the linked Newsroom AI article for FullMatchCentre.jsx.
    """
    try:
        match_res = (
            supabase.table("league_matches")
            .select("*")
            .eq("id", match_id)
            .single()
            .execute()
        )
        if not match_res.data:
            raise HTTPException(status_code=404, detail="Match not found")

        match = match_res.data
        home_id = match["home_franchise_id"]
        away_id = match["away_franchise_id"]

        profiles_res = (
            supabase.table("franchise_public_profiles")
            .select(
                "franchise_id, primary_name, secondary_name, abbreviated_name, "
                "coach_name, primary_logo_url, wordmark_logo_url, simplified_logo_url, "
                "primary_color, secondary_color, accent_color, recent_form"
            )
            .in_("franchise_id", [home_id, away_id])
            .execute()
        )

        profiles_map = {p["franchise_id"]: p for p in (profiles_res.data or [])}
        if home_id not in profiles_map or away_id not in profiles_map:
            raise HTTPException(status_code=404, detail="Franchise public profile missing")

        home_profile = FranchiseBrandingPayload(**profiles_map[home_id])
        away_profile = FranchiseBrandingPayload(**profiles_map[away_id])

        lineups_res = (
            supabase.table("match_lineups")
            .select(
                "franchise_id, slot_number, player_id, assigned_position, "
                "leadership_role, availability_status, live_score, projected_score, "
                "players(full_name, headshot_url, primary_position)"
            )
            .eq("match_id", match_id)
            .in_("franchise_id", [home_id, away_id])
            .execute()
        )

        all_slots = lineups_res.data or []
        home_slots = [s for s in all_slots if s["franchise_id"] == home_id]
        away_slots = [s for s in all_slots if s["franchise_id"] == away_id]

        article_res = (
            supabase.table("newsroom_articles")
            .select("title, summary, content, category")
            .eq("match_id", match_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        ai_article = article_res.data[0] if article_res.data else None

        return MatchCentreResponse(
            match_id=match["id"],
            league_id=match["league_id"],
            round_number=match["round_number"],
            status=match.get("status", "upcoming"),
            home_team=home_profile,
            away_team=away_profile,
            home_score=float(match.get("home_score", 0.0)),
            away_score=float(match.get("away_score", 0.0)),
            home_projected=float(match.get("home_projected_score", 0.0)),
            away_projected=float(match.get("away_projected_score", 0.0)),
            home_lineup=_format_lineup_slots(home_slots),
            away_lineup=_format_lineup_slots(away_slots),
            ai_article=ai_article,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
