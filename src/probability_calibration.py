from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_TEMPERATURE = 1.12
DEFAULT_PROBABILITY_FLOOR = 0.04
DEFAULT_SHRINKAGE_K = 20.0


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


def build_confederation_correction_factors(
    test_frame: pd.DataFrame,
    raw_probabilities: np.ndarray,
    *,
    shrinkage_k: float = DEFAULT_SHRINKAGE_K,
    target_order: tuple[str, str, str] = ("away_win", "draw", "home_win"),
) -> dict[str, tuple[np.ndarray, np.ndarray, float]]:
    """Compute per-confederation-pair correction factors using empirical Bayes shrinkage.

    Returns:
        dict mapping confederation_pair → (empirical_freq, model_avg, alpha_weight)
    """
    pairs = test_frame["confederation_pair"].reset_index(drop=True)
    y_true = test_frame["outcome"]
    outcome_to_idx = {label: idx for idx, label in enumerate(target_order)}
    y_idx = y_true.map(outcome_to_idx).to_numpy()

    corrections: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}

    for pair_name in pairs.unique():
        mask = pairs.eq(pair_name).to_numpy()
        n = mask.sum()
        if n < 3:
            continue

        # Empirical frequency of each outcome
        empirical = np.zeros(len(target_order))
        for k, _ in enumerate(target_order):
            empirical[k] = (y_idx[mask] == k).mean()

        # Model average probability
        model_avg = raw_probabilities[mask].mean(axis=0)

        # Bayesian shrinkage weight
        alpha = n / (n + shrinkage_k)

        corrections[pair_name] = (empirical, model_avg, alpha)

    return corrections


def apply_confederation_correction(
    probabilities: np.ndarray,
    confederation_pairs: pd.Series,
    corrections: dict[str, tuple[np.ndarray, np.ndarray, float]],
) -> np.ndarray:
    """Apply per-confederation-pair Bayesian correction to predicted probabilities."""
    corrected = probabilities.copy()

    for pair_name, (empirical, model_avg, alpha) in corrections.items():
        mask = confederation_pairs.eq(pair_name).to_numpy()
        if not mask.any():
            continue

        pair_probs = probabilities[mask]
        adjusted = pair_probs * (1 - alpha) + empirical * alpha
        adjusted = normalize_probabilities(adjusted)
        corrected[mask] = adjusted

    return corrected
