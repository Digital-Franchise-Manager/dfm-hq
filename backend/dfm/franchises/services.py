from fastapi import HTTPException
from typing import Dict, Any

class FranchiseService:
    @staticmethod
    def compile_ai_prompt(config: Dict[str, Any], primary_name: str, secondary_name: str) -> str:
        """
        Translates wizard choices and colour palette into an elite sports-branding 
        prompt adhering to NFL, FIFA, NBA, NRL, and AFL standards.
        """
        logo_type = config.get("logo_type")
        desc = config.get("custom_description", "")
        
        prompt = (
            f"Professional elite sports franchise branding for '{primary_name} {secondary_name}'. "
            f"Style archetype: {logo_type}. High-end vector graphics, clean lines, "
            f"suitable for NFL, FIFA, NBA, NRL, and AFL standards. {desc}"
        )
        return prompt

    @staticmethod
    async def verify_user_not_registered(supabase_client, user_id: str):
        """
        Ensures franchise identity registration happens strictly once.
        """
        response = supabase_client.table("franchises").select("id, is_locked").eq("user_id", user_id).execute()
        if response.data:
            raise HTTPException(
                status_code=400, 
                detail="Franchise identity has already been established. Initial registration can only occur once."
            )

    @staticmethod
    async def verify_league_lockout(supabase_client, franchise_id: str):
        """
        Blocks edits if the franchise is actively competing in a head-to-head league.
        """
        response = supabase_client.table("league_participants").select("active").eq("franchise_id", franchise_id).eq("active", True).execute()
        if response.data:
            raise HTTPException(
                status_code=403,
                detail="Action denied: Franchise identity parameters cannot be changed while competing in an active league."
            )
