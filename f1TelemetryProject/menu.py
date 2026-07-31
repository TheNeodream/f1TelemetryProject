#!/usr/bin/env python3
"""
menu.py — interaktivny vstupny bod pre f1viz.

Ziadne argumenty prikazoveho riadku. Program vedie pouzivatela
krok po kroku: rocnik -> zavod (z realneho kalendara danej sezony)
-> session -> dvaja jazdci. Potom vykresli delta najrychlejsich kol
(rovnaka logika ako run.py, len bez argparse).

    python menu.py

Poznamka k architekture: fastest_lap() je tu zamerne duplikovana
z run.py, nie importovana odtial. run.py je CLI vstupny bod, nie
kniznica — rovnaky vzor, aky uz projekt pouziva pre "domenovu
logiku" oddelenu od f1viz.analysis (cisté funkcie) a f1viz.plots
(hlupe kreslenie). Druhy vstupny bod duplikuje glue kod, nie fyziku.
"""

from __future__ import annotations

import datetime as dt
import sys

from f1viz.acquisition import init_cache, load_session, get_event_schedule

# Mapa oficialnych nazvov relacii (fastf1) na kody pouzivane
# v run.py/inspect_session.py. 'Sprint Shootout' bol nazov len
# v sezone 2023, 'Sprint Qualifying' pred/po nom — mapujem oba,
# nech menu.py neumre na jednom rocniku.
SESSION_LABEL_TO_CODE = {
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3",
    "Qualifying": "Q",
    "Sprint Qualifying": "SQ",
    "Sprint Shootout": "SQ",
    "Sprint": "S",
    "Race": "R",
}


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n[prerusene]")
        sys.exit(130)


# --------------------------------------------------------------------------
# Kroky menu
# --------------------------------------------------------------------------
def pick_year() -> int:
    current = dt.date.today().year
    raw = ask(f"Rocnik [{current}]: ")
    year = int(raw) if raw else current
    if year < 1950:
        raise SystemExit("[chyba] rocnik mimo rozsahu F1.")
    return year


def pick_event(year: int):
    """Vrati jeden riadok (Event) z kalendara — pouzivatel vybera
    podla cisla kola alebo (ciastocneho) nazvu zavodu."""
    schedule = get_event_schedule(year)  # testy uz vyfiltrovane v acquisition
    races = schedule.sort_values("RoundNumber")
    if races.empty:
        raise SystemExit(f"[chyba] pre rocnik {year} nie je kalendar dostupny.")

    today = dt.date.today()
    print(f"\n=== kalendar {year} ===")
    for _, row in races.iterrows():
        race_day = row["EventDate"].date()
        tag = "  (buduci — data este nemusia byt)" if race_day > today else ""
        print(f"  {int(row['RoundNumber']):>2}. {row['EventName']}{tag}")

    raw = ask("\nZavod (cislo kola alebo nazov): ")
    if raw.isdigit():
        match = races[races["RoundNumber"] == int(raw)]
    else:
        match = races[races["EventName"].str.contains(raw, case=False, na=False)]

    if match.empty:
        raise SystemExit(f"[chyba] zavod '{raw}' sa v kalendari {year} nenasiel.")
    if len(match) > 1:
        print(f"[info] '{raw}' sedi na viac zavodov, beriem prvy zhodny.")
    return match.iloc[0]


def pick_session(event) -> str:
    """Ponukne len tie relacie, ktore dany vikend realne ma
    (sprint vikend != klasicky vikend — Session1..Session5 sa lisia)."""
    codes = []
    print(f"\n=== session — {event['EventName']} ===")
    for i in range(1, 6):
        label = event.get(f"Session{i}")
        if not isinstance(label, str) or not label:
            continue
        code = SESSION_LABEL_TO_CODE.get(label, label.upper()[:2])
        codes.append(code)
        print(f"  {code:<3} {label}")

    raw = ask("\nSession: ").upper()
    if raw not in codes:
        raise SystemExit(
            f"[chyba] session '{raw}' nie je pre '{event['EventName']}' dostupna. "
            f"Dostupne: {', '.join(codes)}"
        )
    return raw


def pick_drivers(session) -> tuple[str, str]:
    available = sorted(session.laps["Driver"].unique())
    if len(available) < 2:
        raise SystemExit("[chyba] v tejto session su kola menej ako dvoch jazdcov.")

    print("\n=== jazdci s kolami v tejto session ===")
    print("  " + ", ".join(available))

    ref = ask("\nReferencny jazdec: ").upper()
    if ref not in available:
        raise SystemExit(f"[chyba] '{ref}' nema v tejto session kola.")

    cmp_ = ask("Porovnavany jazdec: ").upper()
    if cmp_ not in available:
        raise SystemExit(f"[chyba] '{cmp_}' nema v tejto session kola.")
    if cmp_ == ref:
        raise SystemExit("[chyba] potrebujem dvoch roznych jazdcov, nie jedneho dvakrat.")

    return ref, cmp_


def fastest_lap(session, code: str):
    """Najrychlejsie kolo jazdca; hlasne zlyha, ak jazdec v relacii nie je.
    (Duplicitne s run.py — zamerne, pozri docstring modulu.)"""
    laps = session.laps.pick_drivers(code)
    if laps.empty:
        available = sorted(session.laps["Driver"].unique())
        raise SystemExit(
            f"[chyba] jazdec '{code}' nema v tejto relacii kola. "
            f"Dostupni: {', '.join(available)}"
        )
    lap = laps.pick_fastest()
    if lap is None or lap.empty:
        raise SystemExit(f"[chyba] jazdec '{code}' nema platne meratelne kolo.")
    return lap


# --------------------------------------------------------------------------
# Hlavny beh
# --------------------------------------------------------------------------
def main() -> int:
    init_cache()

    year = pick_year()
    event = pick_event(year)
    ident = pick_session(event)

    print(f"\n[nacitavam] {event['EventName']} {year} — {ident} ...")
    session = load_session(year, int(event["RoundNumber"]), ident)

    ref_code, cmp_code = pick_drivers(session)
    ref = fastest_lap(session, ref_code)
    cmp_ = fastest_lap(session, cmp_code)

    # importy az tu, nech pick_year()/pick_event() nemusia cakat
    # na matplotlib, ked pouzivatel len skusa kalendar
    from f1viz.analysis import lap_delta, sector_matrix
    from f1viz import plots
    import matplotlib.pyplot as plt

    print("\n--- sektorova matica ---")
    print(sector_matrix(session.laps).round(3).to_string())

    ref_t, cmp_t = ref["LapTime"], cmp_["LapTime"]
    faster = ref_code if ref_t <= cmp_t else cmp_code
    gap = abs((ref_t - cmp_t).total_seconds())
    print(f"\n--- najrychlejsie kolo: {ref_code} {ref_t} | {cmp_code} {cmp_t} "
          f"| {faster} rychlejsi o {gap:.3f}s ---")

    plots.setup()
    plots.plot_delta(lap_delta(ref, cmp_), ref_code, cmp_code)
    plt.tight_layout()
    plt.show()

    return 0


if __name__ == "__main__":
    sys.exit(main())
