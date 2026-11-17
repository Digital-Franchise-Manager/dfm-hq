"""Head-to-head probability model."""

from ..probability import logistic_probability


def calculate_head_to_head_probabilities(
    home_projection: float,
    away_projection: float,
    score_margin_scale: float = 35.0,
) -> tuple[float, float]:
    """Estimate a two-outcome result from the projected fantasy-score margin.

    The default scale is an initial transparent heuristic, not a fitted or
    historically calibrated parameter. Production calibration requires verified
    historical fantasy results and an explicit model-version change.
    """
    home_probability = logistic_probability(
        home_projection - away_projection,
        score_margin_scale,
    )
    # Keep both selections strictly inside (0, 1) for valid decimal prices.
    epsilon = 1e-12
    home_probability = min(1.0 - epsilon, max(epsilon, home_probability))
    return home_probability, 1.0 - home_probability
