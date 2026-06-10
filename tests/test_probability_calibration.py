import numpy as np
import pytest

from src.probability_calibration import (
    apply_probability_floor,
    apply_temperature_scaling,
    apply_upset_protection,
)


def test_temperature_scaling_softens_extreme_probabilities() -> None:
    probabilities = np.array([[0.9, 0.07, 0.03]])

    scaled = apply_temperature_scaling(probabilities, temperature=1.2)

    assert round(float(scaled.sum()), 8) == 1.0
    assert scaled[0, 0] < probabilities[0, 0]
    assert scaled[0, 2] > probabilities[0, 2]


def test_probability_floor_preserves_normalized_rows() -> None:
    probabilities = np.array([[0.97, 0.02, 0.01]])

    protected = apply_probability_floor(probabilities, floor=0.04)

    assert round(float(protected.sum()), 8) == 1.0
    assert protected.min() >= 0.04


def test_upset_protection_rejects_invalid_parameters() -> None:
    probabilities = np.array([[0.5, 0.3, 0.2]])

    with pytest.raises(ValueError, match="temperature"):
        apply_upset_protection(probabilities, temperature=0.0)

    with pytest.raises(ValueError, match="floor"):
        apply_upset_protection(probabilities, floor=0.4)
