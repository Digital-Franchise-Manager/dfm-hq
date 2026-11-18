"""Translate verified NRL injury facts into Draft league context.

This adapter is deliberately pure: it does not query guessed Supabase tables.
The caller must supply roster ownership resolved by an authorised Draft service.
"""
from collections.abc import Mapping
class DraftNewsTranslator:
    @staticmethod
    async def translate_real_world_injury_to_draft(*,league_id:str,player_name:str,player_id:str,injury_details:str,real_world_team:str,franchise:Mapping[str,str]|None=None)->dict[str,str]:
        if not all(v.strip() for v in (league_id,player_name,player_id,injury_details,real_world_team)):
            raise ValueError("league, player, injury and real-world team details are required")
        if franchise:
            abbrev=franchise.get("abbreviated_name","").strip()
            primary=franchise.get("primary_name","").strip()
            secondary=franchise.get("secondary_name","").strip()
            owner_text=f"The {primary} {secondary} ({abbrev})".strip()
            headline=f"SQUAD BLOW FOR {abbrev}:"
            ownership_status="rostered"
        else:
            owner_text="Unrestricted Free Agent market"
            headline="WAIVER WIRE ALERT:"
            ownership_status="free_agent"
        title=f"{headline} {player_name} ({injury_details})"
        summary=f"{owner_text} face a setback as {player_name} of {real_world_team} is sidelined."
        content=(f"Verified injury information confirms that {player_name} ({real_world_team}) has suffered {injury_details}. "
                 f"This affects the {league_id} Draft competition and {owner_text}.")
        return {"title":title,"summary":summary,"content":content,"ownership_status":ownership_status}
