#!/usr/bin/env python3
"""Diagnostika: co presne mas stiahnute.

Toto spusti PRVE. Nekresli nic. Iba zisti, ci su data uplne
a ktore kanaly telemetrie realne existuju v roku 2026.

    python inspect_session.py 2026 Belgium FP3
"""

from __future__ import annotations

import sys

from f1viz.acquisition import init_cache, load_session

EXPECTED_CAR_CHANNELS = [
    "Speed", "RPM", "nGear", "Throttle", "Brake", "DRS",
]
# Kanaly, ktore by DAVALI ZMYSEL pod pravidlami 2026, ale
# v oficialnom feede zatial nie su. Skript overi realitu, nie dojmy.
SPECULATIVE_2026_CHANNELS = [
    "BatterySOC", "MGUKDeployment", "ERSDeployment", "Override", "PowerMode",
]


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2

    year, gp, ident = int(sys.argv[1]), sys.argv[2], sys.argv[3]

    init_cache()
    s = load_session(year, gp, ident)

    print(f"\n=== {s.event['EventName']} — {s.name} ===")
    print(f"date: {s.date}")

    laps = s.laps
    print(f"\nkol celkom:        {len(laps)}")
    print(f"jazdcov:           {laps['Driver'].nunique()}")
    print(f"presnych kol:      {len(laps.pick_accurate())}")
    print(f"'quicklaps':       {len(laps.pick_quicklaps())}")

    # --- uplnost dat: tu sa lame vacsina projektov ---
    print("\n--- chybajuce hodnoty v klucovych stlpcoch ---")
    key_cols = [
        "LapTime", "Sector1Time", "Sector2Time", "Sector3Time",
        "SpeedI1", "SpeedI2", "SpeedFL", "SpeedST",
        "Compound", "TyreLife", "Stint", "TrackStatus",
    ]
    for col in key_cols:
        if col not in laps.columns:
            print(f"  {col:<15} STLPEC NEEXISTUJE")
            continue
        missing = laps[col].isna().sum()
        print(f"  {col:<15} {missing:>4} / {len(laps)} chyba")

    # --- realne kanaly telemetrie ---
    print("\n--- kanaly telemetrie (z najrychlejsieho kola) ---")
    try:
        fastest = laps.pick_fastest()
        car = fastest.get_car_data()
        pos = fastest.get_pos_data()
        present = list(car.columns)
        print(f"  car_data: {present}")
        print(f"  pos_data: {list(pos.columns)}")
        print(f"  vzoriek:  {len(car)}  (~{len(car) / fastest['LapTime'].total_seconds():.1f} Hz)")

        for ch in EXPECTED_CAR_CHANNELS:
            mark = "OK " if ch in present else "CHYBA"
            print(f"  {mark} {ch}")

        print("\n--- hypoteticke kanaly pohonnej jednotky 2026 ---")
        for ch in SPECULATIVE_2026_CHANNELS:
            mark = "JE!" if ch in present else "nie je"
            print(f"  {mark:<7} {ch}")
    except Exception as exc:  # noqa: BLE001
        print(f"  telemetria nedostupna: {exc!r}")

    # --- pouzite zmesi ---
    if "Compound" in laps.columns:
        print("\n--- zmesi ---")
        print(laps["Compound"].value_counts().to_string())

    # --- pace tabulka ---
    print("\n--- najrychlejsie kolo podla jazdca ---")
    quick = laps.pick_quicklaps()
    if len(quick):
        best = quick.groupby("Driver")["LapTime"].min().sort_values()
        ref = best.iloc[0]
        for drv, t in best.items():
            gap = (t - ref).total_seconds()
            print(f"  {drv:<4} {str(t)[10:-3]:<12} +{gap:.3f}")
    else:
        print("  ziadne pouzitelne kola")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
