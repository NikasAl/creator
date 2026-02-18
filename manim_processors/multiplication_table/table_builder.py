"""Utilities for constructing and animating the multiplication table."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from manim import (
    DOWN,
    LEFT,
    RIGHT,
    Square,
    Text,
    UP,
    VGroup,
    Create,
    Scene,
    MoveToTarget,
    FadeIn,
    BLACK,
    WHITE,
    YELLOW,
)
from .constants import (
    CELL_SIZE,
    DEFAULT_STROKE_WIDTH,
    DEFAULT_ZOOM_SCALE,
    HIGHLIGHT_STROKE_WIDTH,
    N,
    PRIME_COLORS,
)
from .number_utils import get_mixed_color, prime_factorization


@dataclass
class CellInfo:
    """Metadata for a single cell in the multiplication table."""

    product: int
    index: int
    center: np.ndarray
    rect: Square


@dataclass
class TableData:
    """Container for all display groups that make up the multiplication table."""

    top_labels: VGroup
    side_labels: VGroup
    cells: VGroup
    cell_contents: VGroup
    table_group: VGroup
    cells_by_value: Dict[int, List[CellInfo]] = field(default_factory=dict)

    def get_primary_cell(self, value: int) -> Optional[CellInfo]:
        """Return the first cell encountered with the requested product value."""
        cells = self.cells_by_value.get(value)
        if not cells:
            return None
        return cells[0]


def build_multiplication_table(
    n: int = N,
    cell_size: float = CELL_SIZE,
    prime_colors: Dict[int, str] | None = None,
) -> TableData:
    """Construct the multiplication table objects without side effects."""
    palette = prime_colors or PRIME_COLORS

    total_width = (n + 1) * cell_size
    total_height = (n + 1) * cell_size

    offset_x = -total_width / 2 + cell_size / 2
    offset_y = total_height / 2 - cell_size / 2

    top_labels = VGroup()
    for j in range(1, n + 1):
        x_pos = offset_x + j * cell_size
        y_pos = offset_y
        label = Text(str(j), font_size=32, color=get_mixed_color(j, palette)).move_to(
            x_pos * RIGHT + y_pos * UP
        )
        top_labels.add(label)

    side_labels = VGroup()
    for i in range(1, n + 1):
        x_pos = offset_x + (n + 1) * cell_size
        y_pos = offset_y - i * cell_size
        label = Text(str(i), font_size=32, color=get_mixed_color(i, palette)).move_to(
            x_pos * RIGHT + y_pos * UP
        )
        side_labels.add(label)

    cells = VGroup()
    cell_contents = VGroup()
    cells_by_value: Dict[int, List[CellInfo]] = {}

    for i in range(1, n + 1):
        for j in range(i, n + 1):
            x_pos = offset_x + j * cell_size
            y_pos = offset_y - i * cell_size

            rect = Square(side_length=cell_size - 0.05)
            rect.move_to(x_pos * RIGHT + y_pos * UP)
            rect.set_stroke(width=DEFAULT_STROKE_WIDTH)
            # Ensure cells have a solid black fill so opacity animations don't turn them white
            rect.set_fill(BLACK, opacity=1.0)
            cells.add(rect)

            product = i * j
            cell_center = rect.get_center()

            factor_texts = _create_factor_group(i, j, palette, cell_center)
            result_text = Text(
                str(product),
                font_size=32,
                color=get_mixed_color(product, palette),
            ).move_to(cell_center)

            if factor_texts:
                cell_contents.add(factor_texts, result_text)
            else:
                cell_contents.add(result_text)

            cell_info = CellInfo(
                product=product, index=len(cells) - 1, center=cell_center, rect=rect
            )
            cells_by_value.setdefault(product, []).append(cell_info)

    table_group = VGroup(top_labels, side_labels, cells, cell_contents)

    return TableData(
        top_labels=top_labels,
        side_labels=side_labels,
        cells=cells,
        cell_contents=cell_contents,
        table_group=table_group,
        cells_by_value=cells_by_value,
    )


def _create_factor_group(
    value_i: int,
    value_j: int,
    palette: Dict[int, str],
    cell_center: np.ndarray,
) -> Optional[VGroup]:
    factors = prime_factorization(value_i) + prime_factorization(value_j)
    if not factors:
        return None

    factor_texts = VGroup()
    for factor in factors:
        factor_texts.add(
            Text(str(factor), font_size=18, color=palette.get(factor, WHITE))
        )

    factor_texts.arrange_in_grid(rows=1, buff=0.05).scale(0.7)
    factor_texts.move_to(cell_center + 0.25 * DOWN)
    return factor_texts


def animate_table_appearance(scene: Scene, table_data: TableData, run_time: float = 2.0) -> None:
    """Animate the initial appearance of the multiplication table."""
    scene.play(
        FadeIn(table_data.top_labels, shift=DOWN),
        FadeIn(table_data.side_labels, shift=LEFT),
        Create(table_data.cells),
        FadeIn(table_data.cell_contents),
        run_time=run_time,
    )
    scene.wait(1)


class TableAnimator:
    """Encapsulate animations that manipulate the entire table."""

    def __init__(
        self,
        table_data: TableData,
        zoom_scale: float = DEFAULT_ZOOM_SCALE,
        highlight_width: float = HIGHLIGHT_STROKE_WIDTH,
        default_width: float = DEFAULT_STROKE_WIDTH,
    ) -> None:
        self.table_data = table_data
        self.table_group = table_data.table_group
        self.zoom_scale = zoom_scale
        self.highlight_width = highlight_width
        self.default_width = default_width
        self._active_cell: Optional[CellInfo] = None

    def prepare_for_story(self) -> None:
        """Snapshot the current state before a zoom-in sequence."""
        self.table_group.save_state()

    def highlight_cell(self, scene: Scene, cell: CellInfo, run_time: float = 0.5) -> None:
        """Visually highlight the selected cell."""
        scene.play(
            cell.rect.animate.set_stroke(color=YELLOW, width=self.highlight_width),
            run_time=run_time,
        )
        self._active_cell = cell

    def zoom_to_cell(self, scene: Scene, cell: CellInfo, run_time: float = 2.0) -> None:
        """Zoom into the provided cell."""
        table_group = self.table_group
        group_center = table_group.get_center()
        offset = cell.center - group_center

        table_group.generate_target()
        table_group.target.scale(self.zoom_scale)
        table_group.target.shift(-group_center - offset * self.zoom_scale)

        scene.play(MoveToTarget(table_group), run_time=run_time)
        scene.wait(0.5)

    def fade_out_table(self, scene: Scene, run_time: float = 1.0) -> None:
        """Hide the table to make room for the story."""
        scene.play(self.table_group.animate.set_opacity(0), run_time=run_time)
        scene.wait(0.3)

    def restore_after_story(self, scene: Scene, run_time: float = 1.5) -> None:
        """Return the table to its saved state and make it visible again."""
        self.table_group.restore()
        if self._active_cell:
            self._active_cell.rect.set_stroke(width=self.default_width)
            self._active_cell = None

        self.table_group.set_opacity(0)
        scene.play(self.table_group.animate.set_opacity(1), run_time=run_time)
        self.table_group.save_state()
        scene.wait(0.5)

