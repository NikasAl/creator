"""Backward-compatible entry point for the multiplication table animation."""

from manim_processors.multiplication_table.scene import (
    MultiplicationTableScene as _MultiplicationTableScene,
)


class MultiplicationTableScene(_MultiplicationTableScene):
    pass


__all__ = ["MultiplicationTableScene"]