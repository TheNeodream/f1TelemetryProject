"""Vrstva 4 — RENDERING.

Hlupa vrstva. Nic nepocita. Dostane DataFrame, nakresli ho.
Ak sa ti sem zacne pchat vypocet, patri do analysis.py.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import fastf1.plotting as f1plt


def setup(dark: bool = True) -> None:
    f1plt.setup_mpl(
        mpl_timedelta_support=True,
        color_scheme="fastf1" if dark else None,
    )


def team_color(driver: str, session, fallback: str = "#888888") -> str:
    """Konstanty timov pre 2026 su v FastF1 zatial PREDBEZNE.

    Preto nikdy nevolaj get_team_color priamo z kresliaceho kodu.
    Tento wrapper je jediny bod, ktory sa bude musiet opravit,
    az sa palety ustalia.
    """
    try:
        return f1plt.get_driver_color(driver, session=session)
    except Exception:  # noqa: BLE001
        return fallback


def plot_delta(df, ref_name: str, cmp_name: str, ax=None):
    ax = ax or plt.subplots(figsize=(11, 4))[1]
    ax.axhline(0.0, lw=0.8, color="w", alpha=0.4)
    ax.plot(df["Distance"], df["Delta"], lw=1.6)
    ax.fill_between(df["Distance"], 0, df["Delta"], alpha=0.18)
    ax.set_xlabel("vzdialenost [m]")
    ax.set_ylabel(f"delta [s]  ({cmp_name} vs {ref_name})")
    ax.set_title(f"{cmp_name} vs {ref_name} — zaporne = {cmp_name} rychlejsi")
    return ax


def plot_degradation(df, ax=None):
    ax = ax or plt.subplots(figsize=(9, 5))[1]
    ax.barh(
        [f"{r.Driver} S{r.Stint} {r.Compound}" for r in df.itertuples()],
        df["DegSecPerLap"],
    )
    ax.set_xlabel("sklon [s / kolo]  — pozor, zahrna aj ubytok paliva")
    return ax
