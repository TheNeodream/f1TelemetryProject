"""Vrstva 1 — ACQUISITION.

Jediny modul v projekte, ktory vie o existencii FastF1.
Ak sa zajtra zmeni zdroj dat, menis len tento subor.
"""

from __future__ import annotations

import logging
from pathlib import Path

import fastf1

log = logging.getLogger(__name__)

DEFAULT_CACHE = Path.home() / ".cache" / "f1viz"


def init_cache(cache_dir: Path | str = DEFAULT_CACHE) -> None:
    """Cache nie je optimalizacia, je to podmienka fungovania.

    Jedna session ma 50-100 MB. Bez cache bijes API pri kazdom
    reste procesu a dostanes rate limit.
    """
    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(path))
    log.info("cache: %s", path)


def load_session(
    year: int,
    gp: str | int,
    identifier: str,
    *,
    telemetry: bool = True,
    weather: bool = True,
    messages: bool = True,
):
    """identifier: 'FP1' | 'FP2' | 'FP3' | 'Q' | 'S' | 'SQ' | 'R'"""
    session = fastf1.get_session(year, gp, identifier)
    session.load(
        laps=True,
        telemetry=telemetry,
        weather=weather,
        messages=messages,
    )
    return session
