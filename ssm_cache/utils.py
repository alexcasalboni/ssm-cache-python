from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime, timezone
from typing import TypeVar

T = TypeVar("T")


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def batch(iterable: Sequence[T], num: int) -> Iterator[Sequence[T]]:
    """Turn iterable into batches of size num."""
    length = len(iterable)

    for ndx in range(0, length, num):
        yield iterable[ndx : min(ndx + num, length)]
