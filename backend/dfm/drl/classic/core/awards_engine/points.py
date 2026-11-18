"""Confirmed award-point schedule for classic."""
from .models import AwardCategory
POINTS={AwardCategory.MOTM:2,AwardCategory.MOTR:3,}
# Play of the Week is achievement-only until its points are confirmed.
