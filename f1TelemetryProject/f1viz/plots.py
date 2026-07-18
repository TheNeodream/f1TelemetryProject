"""Layer 4 — RENDERING.

Dumb layer. Computes nothing. Gets a DataFrame, draws it.
If a computation starts creeping in here, it belongs in analysis.py.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import fastf1.plotting as f1plt


def setup(dark: bool = True) -> None:
    """Initialize matplotlib styling for FastF1 plots.

    Must be called once before any plot_* function, otherwise
    timedelta axes and team colors won't render correctly.
    """
    f1plt.setup_mpl(
        mpl_timedelta_support=True,
        color_scheme="fastf1" if dark else None,
    )


def team_color(driver: str, session, fallback: str = "#888888") -> str:
    """2026 team color constants in FastF1 are still PROVISIONAL.

    Never call get_team_color directly from plotting code because
    of this. This wrapper is the single point that will need to
    change once the palettes are finalized.
    """
    try:
        return f1plt.get_driver_color(driver, session=session)
    except Exception:  # noqa: BLE001
        return fallback


def plot_delta(df, ref_name: str, cmp_name: str, ax=None):
    """Plot lap_delta() output: delta time vs. distance."""
    if ax is None:
        ax = plt.subplots(figsize=(11, 4))[1]
    ax.axhline(0.0, lw=0.8, color="w", alpha=0.4)
    ax.plot(df["Distance"], df["Delta"], lw=1.6)
    ax.fill_between(df["Distance"], 0, df["Delta"], alpha=0.18)
    ax.set_xlabel("vzdialenost [m]")
    ax.set_ylabel(f"delta [s]  ({cmp_name} vs {ref_name})")
    ax.set_title(f"{cmp_name} vs {ref_name} — zaporne = {cmp_name} rychlejsi")
    return ax


def plot_degradation(df, ax=None):
    """Plot stint_degradation() output: one bar per stint."""
    if ax is None:
        ax = plt.subplots(figsize=(9, 5))[1]
    ax.barh(
        [f"{r.Driver} S{r.Stint} {r.Compound}" for r in df.itertuples()],
        df["DegSecPerLap"],
    )
    ax.set_xlabel("sklon [s / kolo]  — pozor, zahrna aj ubytok paliva")
    return ax