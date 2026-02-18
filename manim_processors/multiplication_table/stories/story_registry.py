"""Registry of all available number stories."""

from __future__ import annotations

from typing import Iterable, List, Sequence

from .base_story import NumberStory
from .story_one import NumberOneStory
from .story_two import NumberTwoStory


def get_story_sequence() -> Sequence[NumberStory]:
    """Return the ordered collection of stories to play."""
    return _STORY_SEQUENCE


_STORY_SEQUENCE: List[NumberStory] = [
    # NumberOneStory(),
    NumberTwoStory(),
]

