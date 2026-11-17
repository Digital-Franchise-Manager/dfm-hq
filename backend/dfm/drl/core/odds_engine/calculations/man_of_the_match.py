"""Man of the Match player probability model."""

from collections.abc import Mapping

from ..probability import softmax


def calculate_man_of_the_match_probabilities(
    player_projected_scores: Mapping[str, float],
    temperature: float = 10.0,
) -> dict[str, float]:
    """Convert supplied player projections into a normalised player distribution."""
    if len(player_projected_scores) < 2:
        raise ValueError("Man of the Match requires at least two player selections")
    if any(not player_id.strip() for player_id in player_projected_scores):
        raise ValueError("player identifiers must not be blank")
    player_ids = list(player_projected_scores.keys())
    probabilities = softmax(list(player_projected_scores.values()), temperature)
    return dict(zip(player_ids, probabilities, strict=True))
