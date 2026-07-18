#!/usr/bin/env python3
"""
run.py — CLI vstupny bod pre f1viz.

Example:
    python run.py 2026 Belgium Q VER ANT
    python run.py 2026 Belgium Q VER ANT LEC --no-sectors
    python run.py 2026 Belgium FP3 VER ANT --save out/spa_delta.png
    python run.py 2026 Spa R VER --sectors-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SESSIONS = ["FP1", "FP2", "FP3", "Q", "SQ", "S", "R"]


# --------------------------------------------------------------------------
# CLI definicia
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run.py",
        description="Analyza a vizualizacia F1 dat (sektorova matica + lap delta).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    p.add_argument("year", type=int, help="rocnik sezony, napr. 2026")
    p.add_argument("gp", help="nazov GP alebo okruhu, napr. Belgium / Spa / 13")
    p.add_argument(
        "session",
        type=str.upper,
        choices=SESSIONS,
        metavar="SESSION",
        help=f"typ relacie: {', '.join(SESSIONS)}",
    )
    p.add_argument(
        "drivers",
        nargs="*",
        type=str.upper,
        metavar="DRIVER",
        help="kody jazdcov; prvy je referencia pre delta (napr. VER ANT)",
    )

    out = p.add_argument_group("vystup")
    out.add_argument("--save", type=Path, metavar="PATH",
                     help="ulozi graf do suboru namiesto zobrazenia okna")
    out.add_argument("--dpi", type=int, default=150, help="DPI pri --save (def. 150)")
    out.add_argument("--no-sectors", action="store_true",
                     help="preskoci sektorovu maticu")
    out.add_argument("--sectors-only", action="store_true",
                     help="len sektorova matica, ziadny graf")

    cache = p.add_argument_group("cache")
    cache.add_argument("--cache-dir", type=Path, default=None,
                       help="adresar cache pre FastF1")

    return p


def validate(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Kontrola kombinacii, ktore argparse sam nezachyti."""
    if args.no_sectors and args.sectors_only:
        parser.error("--no-sectors a --sectors-only sa vylucuju")
    if not args.sectors_only and len(args.drivers) != 2:
        parser.error("delta graf potrebuje presne 2 jazdcov "
                     "(alebo pouzi --sectors-only)")
    if args.year < 1950:
        parser.error("rocnik mimo rozsahu F1")


# --------------------------------------------------------------------------
# Domenova logika
# --------------------------------------------------------------------------
def fastest_lap(session, code: str):
    """Najrychlejsie kolo jazdca; hlasne zlyha, ak jazdec v relacii nie je."""
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


def run(args: argparse.Namespace) -> int:
    # importy az tu — `--help` potom nemusi cakat na nacitanie FastF1/matplotlib
    from f1viz.acquisition import init_cache, load_session
    from f1viz.analysis import sector_matrix, lap_delta
    from f1viz import plots
    import matplotlib.pyplot as plt

    init_cache(args.cache_dir) if args.cache_dir else init_cache()
    session = load_session(args.year, args.gp, args.session)

    if not args.no_sectors:
        print(sector_matrix(session.laps).round(3).to_string())

    if args.sectors_only:
        return 0

    ref_code, cmp_code = args.drivers
    ref = fastest_lap(session, ref_code)
    cmp_ = fastest_lap(session, cmp_code)

    plots.setup()
    plots.plot_delta(lap_delta(ref, cmp_), ref_code, cmp_code)
    plt.tight_layout()

    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(args.save, dpi=args.dpi, bbox_inches="tight")
        print(f"[ok] ulozene: {args.save}")
    else:
        plt.show()

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    validate(args, parser)
    try:
        return run(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())