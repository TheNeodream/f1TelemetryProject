# Step 1: importy z fastf1

from __future__ import annotations

import logging
from pathlib import Path

import fastf1

# logger
log = logging.getLogger(__name__)

DEFAULT_CACHE = Path.home() / ".cache" / "f1viz"

"""
    Parameters
    cache_dir : Path | str
        Pathway to cache. Default DEFAULT_CACHE
        (~/.cache/f1viz). If not present, create one.
"""
def init_cache(cache_dir: Path | str = DEFAULT_CACHE) -> None:

    path = Path(cache_dir)
    path.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(path))
    log.info("cache: %s", path)

"""Download or load data.
    Parameters
    ----------
    year : int
        Rok sezóny, napr. 2026.
    gp : str | int
        Name of GP/circuit ("Spa", "Belgian Grand Prix") or number of GP in calendar.
    identifier : str
        'FP1' | 'FP2' | 'FP3' | 'Q' | 'S' | 'SQ' | 'R'
    telemetry : bool
        Car data (speed, throtle, break, GPS)
    weather : bool
        Weather during seasson.
    messages : bool
        Race control messages.
"""
def load_session(
    year: int,
    gp: str | int,
    identifier: str,
    *,
    telemetry: bool = True,
    weather: bool = True,
    messages: bool = True,
) -> fastf1.core.Session:
    
    session = fastf1.get_session(year, gp, identifier)
    session.load(
        laps=True,
        telemetry=telemetry,
        weather=weather,
        messages=messages,
    )
    return session


"""Kalendar sezony.

    Tenky wrapper okolo fastf1.get_event_schedule. Existuje kvoli
    jednej veci: include_testing=False je defaultne, pretoze
    predsezonne testy nemaju struktury FP/Q/R relacii, ktore
    zvysok f1viz ocakava (sector_matrix, lap_delta) — bez tohto
    filtra by menu.py ponuklo zavod, ktory nevie nic vratit.

    Parameters
    ----------
    year : int
        Rok sezóny, napr. 2026.
    include_testing : bool
        Zahrnut aj predsezonne testy (Round 0). Default False.

    Returns
    -------
    fastf1.events.EventSchedule
        DataFrame so stlpcami RoundNumber, EventName, EventDate,
        EventFormat, Session1..Session5 (nazvy relacii), atd.
"""
def get_event_schedule(year: int, *, include_testing: bool = False):
    schedule = fastf1.get_event_schedule(year, include_testing=include_testing)
    log.info("kalendar %s: %d zavodov", year, len(schedule))
    return schedule
