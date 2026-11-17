from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class FranchiseWizardConfig(BaseModel):
    logo_type: str = Field(..., description="Mascot, Wordmark, Lettermark, Numerical, Geometrical, Geographical, or Hybrid")
    sub_style: Optional[str] = Field(None, description="Specific sub-style configuration based on logo type")
    typography_style: Optional[str] = Field(None, description="Font style if typography/wordmark is selected")
    badge_enabled: bool = Field(..., description="Whether a shield/crest container is used")
    badge_shape: Optional[str] = Field(None, description="Shield, European crest, Circular, etc.")
    badge_pattern: Optional[str] = Field(None, description="Solid, vertical split, horizontal split, etc.")
    custom_description: Optional[str] = Field(None, description="Manager's free-text creative direction prompt")

class FranchiseIdentityCreate(BaseModel):
    user_id: str = Field(..., description="Supabase Auth UUID of the manager")
    primary_name: str = Field(..., min_length=2, max_length=40, description="Location e.g. Campbelltown")
    secondary_name: str = Field(..., min_length=2, max_length=40, description="Mascot / Geographical e.g. Crushers")
    abbreviated_name: str = Field(..., min_length=3, max_length=4, description="3-4 Letter Abbreviation e.g. CRSH")
    
    # Colour Palette (Black and white permitted for contrast)
    primary_colour: str = Field(..., description="Hex code for primary colour")
    secondary_colour: str = Field(..., description="Hex code for secondary colour")
    tertiary_colour: Optional[str] = Field(None, description="Optional hex code for tertiary colour")
    accent_colour: Optional[str] = Field(None, description="Optional hex code for accent colour")
    
    # Wizard configuration and asset recipe
    wizard_config: FranchiseWizardConfig

class IdentityPackResponse(BaseModel):
    franchise_id: str
    primary_logo_url: str
    wordmark_logo_url: str
    simplified_logo_url: str
    regeneration_count: int
    is_locked: bool
