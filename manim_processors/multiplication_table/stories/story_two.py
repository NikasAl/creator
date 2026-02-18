"""Story content for the number two."""

from __future__ import annotations

from manim import GREEN

from ..constants import PRIME_COLORS
from .base_story import NumberStory, TextSpec


class NumberTwoStory(NumberStory):
    number = 2

    title_spec = TextSpec("2", 80, PRIME_COLORS[2])
    role_spec = TextSpec("Наименьшее простое число", 40, "#FFFF00")

    properties_specs = (
        TextSpec("Простое число - ни на что не делится \n кроме 1 и самого себя", 36, PRIME_COLORS[2]),
        TextSpec("Единственное четное простое", 50, PRIME_COLORS[2]),
        TextSpec("2 × n = n + n", 64, GREEN),
    )

    def get_summary_specs(self):
        return (
            TextSpec("Единственное четное простое", 36, PRIME_COLORS[2]),
            TextSpec("2 × n = n + n", 48, GREEN),
        )

