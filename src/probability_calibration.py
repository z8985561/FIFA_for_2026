from __future__ import annotations

import numpy as np

DEFAULT_TEMPERATURE = 1.12
DEFAULT_PROBABILITY_FLOOR = 0.04


def normalize_probabilities(probabilities: np.ndarray) -> np.ndarray:
    working = np.asarray(probabilities, dtype=float)
    totals = working.sum(axis=1, keepdims=True)
    return working / np.clip(totals, 1e-12, None)


def apply_temperature_scaling(
    probabilities: np.ndarray,
    *,
    temperature: float = DEFAULT_TEMPERATURE,
) -> np.ndarray:
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    working = np.asarray(probabilities, dtype=float)
    logits = np.log(np.clip(working, 1e-12, 1.0))
    scaled = np.exp(logits / temperature)
    return normalize_probabilities(scaled)


def apply_probability_floor(
    probabilities: np.ndarray,
    *,
    floor: float = DEFAULT_PROBABILITY_FLOOR,
) -> np.ndarray:
    working = np.asarray(probabilities, dtype=float)
    if floor < 0:
        raise ValueError("floor must be non-negative")
    if floor >= 1.0 / working.shape[1]:
        raise ValueError("floor is too high for the number of outcome classes")
    base_mass = floor * working.shape[1]
    residual = np.clip(working - floor, 0.0, None)
    residual_totals = residual.sum(axis=1, keepdims=True)
    safe_totals = np.clip(residual_totals, 1e-12, None)
    scaled_residual = residual / safe_totals * (1.0 - base_mass)
    floored = floor + scaled_residual
    no_residual_mask = residual_totals.squeeze(axis=1) <= 1e-12
    if np.any(no_residual_mask):
        floored[no_residual_mask] = np.full(working.shape[1], 1.0 / working.shape[1])
    return normalize_probabilities(floored)


def apply_upset_protection(
    probabilities: np.ndarray,
    *,
    temperature: float = DEFAULT_TEMPERATURE,
    floor: float = DEFAULT_PROBABILITY_FLOOR,
) -> np.ndarray:
    scaled = apply_temperature_scaling(probabilities, temperature=temperature)
    return apply_probability_floor(scaled, floor=floor)
