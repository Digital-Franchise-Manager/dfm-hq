"""Full-field DRL premiership probability model."""

from collections.abc import Mapping

from ..probability import softmax

EXPECTED_NRL_CLUBS = 17


def calculate_premiership_probabilities(
    club_power_ratings: Mapping[str, float],
    temperature: float = 1.0,
) -> dict[str, float]:
    """Calculate a normalised premiership distribution for all 17 NRL clubs.

    Ratings must come from the caller's verified competition-intelligence layer.
    This module does not invent clubs, ratings, fixtures or player data.
    """
    if len(club_power_ratings) != EXPECTED_NRL_CLUBS:
        raise ValueError(f"premiership market requires exactly {EXPECTED_NRL_CLUBS} clubs")
    if any(not club_id.strip() for club_id in club_power_ratings):
        raise ValueError("club identifiers must not be blank")
    club_ids = list(club_power_ratings.keys())
    probabilities = softmax(list(club_power_ratings.values()), temperature)
    return dict(zip(club_ids, probabilities, strict=True))
