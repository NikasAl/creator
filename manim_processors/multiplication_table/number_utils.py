"""Number-theoretic helpers and color utilities used across the animation."""

from __future__ import annotations

from collections import Counter
from typing import Dict

import numpy as np

from manim import WHITE, color_to_rgb, rgb_to_color

from .constants import DEFAULT_NEUTRAL_COLOR, PRIME_COLORS


def prime_factorization(n: int) -> list[int]:
    """Return the multiset of prime factors of ``n``."""
    if n <= 1:
        return []

    factors: list[int] = []
    divisor = 2
    remainder = n

    while divisor * divisor <= remainder:
        while remainder % divisor == 0:
            factors.append(divisor)
            remainder //= divisor
        divisor += 1

    if remainder > 1:
        factors.append(remainder)

    return factors


def get_mixed_color(n: int, prime_colors: Dict[int, str] | None = None) -> np.ndarray:
    """Return a color for ``n`` based on the weighted mix of its prime factors."""
    palette = prime_colors or PRIME_COLORS

    if n == 1:
        return rgb_to_color(color_to_rgb(DEFAULT_NEUTRAL_COLOR))

    factors = prime_factorization(n)
    if not factors:
        return rgb_to_color(color_to_rgb(DEFAULT_NEUTRAL_COLOR))

    counts = Counter(factors)
    total = sum(counts.values())

    mixed_rgb = np.array([0.0, 0.0, 0.0])
    for prime, exponent in counts.items():
        weight = exponent / total
        hex_color = palette.get(prime, WHITE)
        mixed_rgb += weight * color_to_rgb(hex_color)

    return rgb_to_color(mixed_rgb)

