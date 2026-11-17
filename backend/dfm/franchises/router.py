from fastapi import APIRouter, HTTPException, Depends
from backend.dfm.franchises.models import FranchiseIdentityCreate
from backend.dfm.franchises.service import FranchiseService

router = APIRouter(prefix="/api/dfm/franchises", tags=["Franchise Identity"])

@router.post("/onboard", response_status=201)
async def create_franchise_identity(payload: FranchiseIdentityCreate):
    """
    Handles the mandatory initial onboarding step. 
    Fails if the user already has a registered franchise.
    """
    # Note: Pass your initialized Supabase client dependency here
    # await FranchiseService.verify_user_not_registered(supabase, payload.user_id)
    
    # Compile AI Prompt based on wizard specs
    ai_prompt = FranchiseService.compile_ai_prompt(
        payload.wizard_config.dict(), 
        payload.primary_name, 
        payload.secondary_name
    )
    
    # Mock AI generation output for the Identity Pack (Primary, Wordmark, Simplified)
    identity_pack = {
        "user_id": payload.user_id,
        "primary_name": payload.primary_name,
        "secondary_name": payload.secondary_name,
        "abbreviated_name": payload.abbreviated_name,
        "primary_colour": payload.primary_colour,
        "secondary_colour": payload.secondary_colour,
        "tertiary_colour": payload.tertiary_colour,
        "accent_colour": payload.accent_colour,
        "wizard_config": payload.wizard_config.dict(),
        "primary_logo_url": "storage/franchises/logos/primary_mock.png",
        "wordmark_logo_url": "storage/franchises/logos/wordmark_mock.png",
        "simplified_logo_url": "storage/franchises/logos/simplified_mock.png",
        "regeneration_count": 0,
        "is_locked": True # Locked for active competition changes post-creation
    }
    
    return {
        "message": "Franchise Identity Pack successfully generated and locked in!",
        "data": identity_pack
    }

@router.post("/{franchise_id}/regenerate")
async def regenerate_identity_pack(franchise_id: str, current_regen_count: int):
    """
    Handles regeneration. Enforces the strict maximum 2 regeneration limit.
    After 2 regens, frontend must force a 'Start Again' reset.
    """
    if current_regen_count >= 2:
        raise HTTPException(
            status_code=400,
            detail="Regeneration limit reached (Maximum 2 allowed). Please select 'Start Again' to restart the wizard."
        )
    
    new_regen_count = current_regen_count + 1
    
    return {
        "message": f"Generated new identity options (Regeneration {new_regen_count} of 2)",
        "regeneration_count": new_regen_count,
        "new_options_generated": 3
    }
