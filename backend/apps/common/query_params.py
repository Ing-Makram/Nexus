from __future__ import annotations

from typing import TYPE_CHECKING

from django.utils.dateparse import parse_date

if TYPE_CHECKING:
    from datetime import date


def parse_date_param(value: str | None) -> date | None:
    """A query-param date (``YYYY-MM-DD``), or ``None`` if absent or malformed.

    Malformed input is ignored rather than raising, so a bad ``?date_from=`` on a
    list endpoint just means "no lower bound", never a 500.
    """
    if not value:
        return None
    try:
        return parse_date(value)
    except ValueError:
        return None
