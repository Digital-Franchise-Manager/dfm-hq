class DraftNewsTranslator:
    @staticmethod
    async def translate_real_world_injury_to_draft(
        supabase_client, 
        league_id: str, 
        player_name: str, 
        player_id: str, 
        injury_details: str, 
        real_world_team: str
    ) -> dict:
        """
        Translates a real-world injury update into draft-league context,
        naming the rostered franchise or flagging them as a Free Agent.
        """
        roster_query = supabase_client.table("league_rosters") \
            .select("franchises(primary_name, secondary_name, abbreviated_name)") \
            .eq("league_id", league_id) \
            .eq("player_id", player_id) \
            .execute()
        
        if roster_query.data and len(roster_query.data) > 0:
            franchise = roster_query.data[0].get("franchises", {})
            p_name = franchise.get("primary_name", "")
            s_name = franchise.get("secondary_name", "")
            abbrev = franchise.get("abbreviated_name", "")
            
            owner_text = f"The {p_name} {s_name} ({abbrev})"
            headline_prefix = f"⚠️ SQUAD BLOW FOR {abbrev}:"
        else:
            owner_text = "Unrestricted Free Agent market"
            headline_prefix = "🔎 WAIVER WIRE ALERT:"

        title = f"{headline_prefix} {player_name} ({injury_details})"
        summary = f"{owner_text} are hit with a major setback as {player_name} (formerly {real_world_team}) faces time on the sidelines."
        content = (
            f"In a major development for your head-to-head league, medical staff have confirmed "
            f"that {player_name} has suffered an injury: {injury_details}. "
            f"This development directly impacts {owner_text}. Managers should review their bench cover immediately."
        )

        return {
            "title": title,
            "summary": summary,
            "content": content,
            "ownership_status": "rostered" if "squad blow" in headline_prefix.lower() else "free_agent"
        }
