"""Primary scene definition that orchestrates the multiplication table animation."""

from __future__ import annotations

from manim import ORIGIN, Scene

from .stories import get_story_sequence
from .table_builder import TableAnimator, animate_table_appearance, build_multiplication_table


class MultiplicationTableScene(Scene):
    """Render the multiplication table and associated number stories."""

    def construct(self) -> None:
        table_data = build_multiplication_table()
        animate_table_appearance(self, table_data)

        animator = TableAnimator(table_data)

        for story in get_story_sequence():
            cell_info = table_data.get_primary_cell(story.number)
            if cell_info is None:
                continue

            animator.prepare_for_story()
            animator.highlight_cell(self, cell_info)
            animator.zoom_to_cell(self, cell_info)
            animator.fade_out_table(self)

            story.play(self, ORIGIN)

            animator.restore_after_story(self)

        self.wait(1)

