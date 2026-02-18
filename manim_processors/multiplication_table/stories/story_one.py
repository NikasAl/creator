"""Story content for the number one."""

from __future__ import annotations

from manim import BLUE, GREEN, GRAY, WHITE

from .base_story import NumberStory, TextSpec


class NumberOneStory(NumberStory):
    number = 1
    title_spec = TextSpec("1", 80, WHITE)
    role_spec = TextSpec("Нейтральный элемент умножения", 40, "#FFFF00")

    properties_specs = (
        TextSpec("1 × n = n", 64, GREEN),
        TextSpec("Начало счёта", 50, BLUE),
        TextSpec("Не простое, не составное", 50, GRAY),
    )

    def get_summary_specs(self):
        return (
            TextSpec("1 × n = n", 48, GREEN),
            TextSpec("Начало счёта", 36, BLUE),
            TextSpec("Не простое, не составное", 36, GRAY),
        )

