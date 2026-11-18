"""Confirmed award-point schedule for draft."""
from .models import AwardCategory
POINTS={AwardCategory.MOTM:2,AwardCategory.MOTR:3,AwardCategory.TOTW:1,}
# Play of the Week is achievement-only until its points are confirmed.
