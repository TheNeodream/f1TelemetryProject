"""Vrstva 3 — ANALYSIS.

Ciste funkcie. Ziadny matplotlib, ziadny print, ziadny I/O.
Vsetko sa da otestovat bez toho, aby si videl obrazok.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastf1.core import Lap, Laps
from fastf1.utils import delta_time


def lap_delta(reference: Lap, comparison: Lap) -> pd.DataFrame:
    """Delta time medzi dvoma kolami ako funkcia vzdialenosti.

    Vracia DataFrame so stlpcami Distance / Delta / SpeedRef / SpeedCmp.
    Zaporna delta = porovnavane kolo je rychlejsie.
    """
    delta, ref_tel, cmp_tel = delta_time(reference, comparison)
    return pd.DataFrame(
        {
            "Distance": ref_tel["Distance"].to_numpy(),
            "Delta": np.asarray(delta, dtype=float),
            "SpeedRef": ref_tel["Speed"].to_numpy(),
        }
    )


def stint_degradation(laps: Laps, driver: str) -> pd.DataFrame:
    """Linearna regresia casu kola vs. vek gumy, pre kazdy stint.

    POZOR na interpretaciu: v tréningu je palivo premenna, ktoru
    nevidis. Klesajuci cas kola nie je dokaz nulovej degradacie —
    je to superpozicia degradacie a ubudajuceho paliva.
    """
    d = laps.pick_drivers(driver).pick_quicklaps().pick_wo_box()
    rows = []
    for stint, grp in d.groupby("Stint"):
        grp = grp.dropna(subset=["LapTime", "TyreLife"])
        if len(grp) < 3:
            continue
        x = grp["TyreLife"].to_numpy(dtype=float)
        y = grp["LapTime"].dt.total_seconds().to_numpy()
        slope, intercept = np.polyfit(x, y, 1)
        rows.append(
            {
                "Driver": driver,
                "Stint": int(stint),
                "Compound": grp["Compound"].iloc[0],
                "Laps": len(grp),
                "DegSecPerLap": float(slope),
                "BaselineSec": float(intercept),
                "BestSec": float(y.min()),
            }
        )
    return pd.DataFrame(rows)


def sector_matrix(laps: Laps) -> pd.DataFrame:
    """Najlepsi cas kazdeho jazdca v kazdom sektore + teoreticke kolo.

    Na Spa je toto najhodnotnejsia jedna tabulka v celom vikende:
    S1 je vykon pohonnej jednotky, S2 pritlak, S3 trakcia a top speed.
    Rozdiel medzi setupmi tam kricí hlasnejsie nez celkovy cas kola.
    """
    q = laps.pick_quicklaps()
    cols = ["Sector1Time", "Sector2Time", "Sector3Time"]
    best = q.groupby("Driver")[cols].min()
    out = best.apply(lambda s: s.dt.total_seconds())
    out["Theoretical"] = out.sum(axis=1)
    out["ActualBest"] = (
        q.groupby("Driver")["LapTime"].min().dt.total_seconds()
    )
    out["Untapped"] = out["ActualBest"] - out["Theoretical"]
    return out.sort_values("Theoretical")


def implied_deployment(lap: Lap, straight_threshold_kmh: int = 250) -> pd.DataFrame:
    """Nepriama sonda do systemu nasadenia energie 2026.

    Oficialny feed NEPOSKYTUJE stav baterie ani vykon MGU-K.
    Jedine, co mas, je dv/dt pri plnom plyne na rovinke.
    Miesto, kde zrychlenie nahle klesne pri konstantnom plyne,
    je kandidat na vycerpanie nasadenia — nie dokaz, hypoteza.
    """
    car = lap.get_car_data().add_distance()
    car = car[(car["Throttle"] > 95) & (car["Speed"] > straight_threshold_kmh)]
    if car.empty:
        return pd.DataFrame(columns=["Distance", "Speed", "AccelMs2"])

    t = car["Time"].dt.total_seconds().to_numpy()
    v = car["Speed"].to_numpy(dtype=float) / 3.6
    accel = np.gradient(v, t)
    return pd.DataFrame(
        {
            "Distance": car["Distance"].to_numpy(),
            "Speed": car["Speed"].to_numpy(),
            "AccelMs2": accel,
        }
    )
