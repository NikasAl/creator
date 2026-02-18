"""Base building blocks for number-specific storytelling segments."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Iterable, Sequence

from manim import DOWN, FadeIn, FadeOut, ORIGIN, Scene, Text, UP, VGroup, Write


@dataclass(frozen=True)
class TextSpec:
    """Data holder that describes a single text element."""

    content: str
    font_size: int
    color: str


class NumberStory(ABC):
    """Reusable template for stories about specific numbers."""

    number: int
    title_spec: TextSpec
    role_spec: TextSpec
    properties_specs: Sequence[TextSpec]

    title_offset = 2.5 * UP
    role_offset = 1.5 * UP

    def play(self, scene: Scene, center) -> None:
        """Render the story using a shared animation flow."""
        title = self._create_text(self.title_spec, center + self.title_offset)
        role = self._create_text(self.role_spec, center + self.role_offset)

        scene.play(Write(title, run_time=1))
        scene.wait(0.5)

        scene.play(Write(role, run_time=1))
        scene.wait(0.5)

        sequential_props = [
            self._create_text(spec, center) for spec in self.properties_specs
        ]

        current_prop = None
        for prop in sequential_props:
            if current_prop is not None:
                scene.play(FadeOut(current_prop), run_time=0.5)
            scene.play(FadeIn(prop, scale=1.2), run_time=0.8)
            scene.wait(5)
            current_prop = prop

        if current_prop is not None:
            scene.play(FadeOut(current_prop), run_time=0.5)

        summary_props = [
            self._create_text(spec, ORIGIN) for spec in self.get_summary_specs()
        ]
        summary_group = VGroup(*summary_props).arrange(DOWN, buff=0.5)
        summary_group.move_to(center)
        scene.play(FadeIn(summary_group, lag_ratio=0.3), run_time=1.5)
        scene.wait(5)

        scene.play(
            FadeOut(title),
            FadeOut(role),
            FadeOut(summary_group),
            run_time=1,
        )

    def get_summary_specs(self) -> Iterable[TextSpec]:
        """Override to customize the summary text specifications."""
        return self.properties_specs

    @staticmethod
    def _create_text(spec: TextSpec, position):
        text = Text(spec.content, font_size=spec.font_size, color=spec.color)
        text.move_to(position)
        return text

