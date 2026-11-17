"""Numerically stable probability functions used by the DRL Odds Engine."""

from __future__ import annotations

import math
from collections.abc import Sequence


def logistic_probability(value: float, scale: float) -> float:
    """Return sigmoid(value / scale) without exponential overflow."""
    if not math.isfinite(value):
        raise ValueError("value must be finite")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be a finite number greater than zero")
    z = value / scale
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1.0 + exp_z)


def softmax(values: Sequence[float], temperature: float = 1.0) -> tuple[float, ...]:
    """Convert finite ratings to a normalised distribution using stable softmax."""
    if len(values) < 2:
        raise ValueError("softmax requires at least two values")
    if not math.isfinite(temperature) or temperature <= 0:
        raise ValueError("temperature must be a finite number greater than zero")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("all softmax inputs must be finite")

    scaled = [value / temperature for value in values]
    maximum = max(scaled)
    exponentials = [math.exp(value - maximum) for value in scaled]
    denominator = math.fsum(exponentials)
    if denominator <= 0 or not math.isfinite(denominator):
        raise ArithmeticError("softmax normalisation failed")
    probabilities = [value / denominator for value in exponentials]

    # Correct the final floating-point residual while preserving positivity.
    residual = 1.0 - math.fsum(probabilities)
    probabilities[-1] += residual
    if any(value <= 0 or value >= 1 for value in probabilities):
        raise ArithmeticError("softmax produced an invalid probability")
    return tuple(probabilities)
