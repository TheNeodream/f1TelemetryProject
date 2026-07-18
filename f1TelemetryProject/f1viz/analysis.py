"""Layer 3 — ANALYSIS.

Pure functions. No matplotlib, no print, no I/O.
Everything must be testable without ever looking at a plot.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastf1.core import Lap, Laps
from fastf1.utils import delta_time


def lap_delta(reference: Lap, comparison: Lap) -> pd.DataFrame:
    """Delta time between two laps as a function of distance.

    Returns a DataFrame with columns Distance / Delta / SpeedRef / SpeedCmp.
    Negative delta = comparison lap is faster.
    """
    delta, ref_tel, cmp_tel = delta_time(reference, comparison)

    # ref_tel a cmp_tel NIE SÚ na spoločnej distance mriežke — cmp_tel má
    # vlastný, nezávislý počet vzoriek (viď FastF1 dokumentáciu k
    # delta_time). delta je počítaná a zarovnaná na ref_tel["Distance"].
    # Preto SpeedCmp treba interpolovať na tú istú os manuálne — inak
    # dostaneš presne ten ValueError: All arrays must be of the same length.
    ref_distance = ref_tel["Distance"].to_numpy(dtype=float)
    cmp_distance = cmp_tel["Distance"].to_numpy(dtype=float)
    cmp_speed = cmp_tel["Speed"].to_numpy(dtype=float)

    speed_cmp_aligned = np.interp(ref_distance, cmp_distance, cmp_speed)

    return pd.DataFrame(
        {
            "Distance": ref_distance,
            "Delta": np.asarray(delta, dtype=float),
            "SpeedRef": ref_tel["Speed"].to_numpy(),
            "SpeedCmp": speed_cmp_aligned,
        }
    )


def stint_degradation(laps: Laps, driver: str) -> pd.DataFrame:
    """Linear regression of lap time vs. tyre age, per stint.

    INTERPRETATION WARNING: in practice sessions fuel load is a
    hidden variable. A falling lap time is not proof of zero
    degradation — it's a superposition of degradation and
    decreasing fuel load. Do not treat DegSecPerLap as a clean
    tyre-only signal outside of a race stint.
    """
    d = laps.pick_drivers(driver).pick_quicklaps().pick_wo_box()
    rows = []
    for stint, grp in d.groupby("Stint"):
        grp = grp.dropna(subset=["LapTime", "TyreLife"])
        if len(grp) < 3:
            # Not enough points for a meaningful linear fit.
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
    """Each driver's best time per sector, plus the theoretical lap.

    At Spa this is the single most informative table of the
    weekend: S1 reflects power unit output, S2 downforce, S3
    traction and top speed. Setup differences show up here louder
    than in the overall lap time.
    """
    q = laps.pick_quicklaps()
    cols = ["Sector1Time", "Sector2Time", "Sector3Time"]
    best = q.groupby("Driver")[cols].min()
    out = best.apply(lambda s: s.dt.total_seconds())
    out["Theoretical"] = out.sum(axis=1)
    out["ActualBest"] = (
        q.groupby("Driver")["LapTime"].min().dt.total_seconds()
    )
    # Untapped = gap between the theoretical best lap (sum of best
    # sectors, possibly from different laps) and the actual best
    # single lap. Large values flag inconsistency, not raw pace.
    out["Untapped"] = out["ActualBest"] - out["Theoretical"]
    return out.sort_values("Theoretical")


def implied_deployment(lap: Lap, straight_threshold_kmh: int = 250) -> pd.DataFrame:
    """Indirect probe into the 2026 energy deployment system.

    The official feed does NOT expose battery state or MGU-K
    output. All you have is dv/dt at full throttle on a straight.
    A sudden drop in acceleration under constant throttle is a
    candidate for deployment running out — not proof, a hypothesis.
    """
    car = lap.get_car_data().add_distance()
    car = car[(car["Throttle"] > 95) & (car["Speed"] > straight_threshold_kmh)]
    if car.empty:
        return pd.DataFrame(columns=["Distance", "Speed", "AccelMs2"])

    t = car["Time"].dt.total_seconds().to_numpy()
    v = car["Speed"].to_numpy(dtype=float) / 3.6  # km/h -> m/s
    accel = np.gradient(v, t)
    return pd.DataFrame(
        {
            "Distance": car["Distance"].to_numpy(),
            "Speed": car["Speed"].to_numpy(),
            "AccelMs2": accel,
        }
    )