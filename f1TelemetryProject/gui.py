#!/usr/bin/env python3
"""
gui.py — graficke menu pre f1viz.

Tkinter (standardna kniznica, ziadna nova zavislost). Rovnaky tok
ako menu.py — rok -> zavod -> session -> dvaja jazdci -> porovnanie
— len kliknutim namiesto pisania do terminalu. Graf je zapusteny
priamo v okne (FigureCanvasTkAgg), nie samostatne matplotlib okno.

Sietove volania (kalendar, stiahnutie session) bezia na vlakne na
pozadi. Tkinter nie je thread-safe, preto vlakno vysledok len vlozi
do queue.Queue a hlavne vlakno ho vyzdvihne v _poll_queue() —
ziadny priamy zapis do UI z workera.

    python gui.py

Vyzaduje systemovy Tk (na Debiane/Ubuntu: apt install python3-tk;
na Windows/macOS je sucastou standardnej instalacie Pythonu).
"""

from __future__ import annotations

import datetime as dt
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from f1viz import plots
from f1viz.acquisition import get_event_schedule, init_cache, load_session
from f1viz.analysis import lap_delta, sector_matrix

# rovnaka mapa ako v menu.py — Sprint Shootout (2023) vs.
# Sprint Qualifying (ostatne rocniky), oboje na kod SQ
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


class F1VizApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("f1viz")
        self.geometry("1150x760")
        self.minsize(900, 600)

        self._work_q: "queue.Queue[tuple[str, object, object]]" = queue.Queue()
        self._schedule = None  # DataFrame kalendara aktualneho rocnika
        self._event = None  # Series — vybrany zavod
        self._session = None  # fastf1 Session — nacitana relacia

        init_cache()
        plots.setup()

        self._build_controls()
        self._build_output()
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------------
    # UI kostra
    # ------------------------------------------------------------------
    def _build_controls(self) -> None:
        bar = ttk.Frame(self, padding=8)
        bar.pack(side="top", fill="x")

        ttk.Label(bar, text="Rok:").pack(side="left")
        self.year_var = tk.StringVar(value=str(dt.date.today().year))
        ttk.Entry(bar, textvariable=self.year_var, width=6).pack(
            side="left", padx=(2, 8)
        )

        self.btn_calendar = ttk.Button(
            bar, text="Nacitat kalendar", command=self._on_load_calendar
        )
        self.btn_calendar.pack(side="left", padx=(0, 14))

        ttk.Label(bar, text="Zavod:").pack(side="left")
        self.event_var = tk.StringVar()
        self.event_combo = ttk.Combobox(
            bar, textvariable=self.event_var, state="disabled", width=34
        )
        self.event_combo.pack(side="left", padx=(2, 8))
        self.event_combo.bind("<<ComboboxSelected>>", self._on_event_selected)

        ttk.Label(bar, text="Session:").pack(side="left")
        self.session_var = tk.StringVar()
        self.session_combo = ttk.Combobox(
            bar, textvariable=self.session_var, state="disabled", width=6
        )
        self.session_combo.pack(side="left", padx=(2, 8))

        self.btn_session = ttk.Button(
            bar, text="Nacitat session", command=self._on_load_session, state="disabled"
        )
        self.btn_session.pack(side="left", padx=(0, 14))

        ttk.Label(bar, text="Jazdec 1:").pack(side="left")
        self.drv1_var = tk.StringVar()
        self.drv1_combo = ttk.Combobox(
            bar, textvariable=self.drv1_var, state="disabled", width=6
        )
        self.drv1_combo.pack(side="left", padx=(2, 8))

        ttk.Label(bar, text="Jazdec 2:").pack(side="left")
        self.drv2_var = tk.StringVar()
        self.drv2_combo = ttk.Combobox(
            bar, textvariable=self.drv2_var, state="disabled", width=6
        )
        self.drv2_combo.pack(side="left", padx=(2, 8))

        self.btn_compare = ttk.Button(
            bar, text="Porovnat", command=self._on_compare, state="disabled"
        )
        self.btn_compare.pack(side="left")

        self.status_var = tk.StringVar(value="pripraveny")
        ttk.Label(
            self, textvariable=self.status_var, padding=(8, 2),
            relief="sunken", anchor="w",
        ).pack(side="bottom", fill="x")

    def _build_output(self) -> None:
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, padding=8)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Sektorova matica", font=("", 10, "bold")).pack(anchor="w")
        self.table = ttk.Treeview(left, show="headings", height=25)
        self.table.pack(fill="y", expand=True)

        right = ttk.Frame(body, padding=8)
        right.pack(side="left", fill="both", expand=True)
        self.fig, self.ax = plt.subplots(figsize=(7, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Async pomocnik — sietove/IO volanie na vlakne, vysledok cez queue
    # ------------------------------------------------------------------
    def _run_async(self, fn, on_done, *args) -> None:
        def worker() -> None:
            try:
                result = fn(*args)
            except Exception as exc:  # noqa: BLE001
                self._work_q.put(("err", None, exc))
            else:
                self._work_q.put(("ok", on_done, result))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self) -> None:
        try:
            status, on_done, payload = self._work_q.get_nowait()
        except queue.Empty:
            pass
        else:
            if status == "ok":
                on_done(payload)
            else:
                self.status_var.set("chyba")
                self._reset_busy_buttons()
                messagebox.showerror("f1viz", str(payload))
        self.after(100, self._poll_queue)

    def _reset_busy_buttons(self) -> None:
        for btn in (self.btn_calendar, self.btn_session, self.btn_compare):
            btn.state(["!disabled"])

    # ------------------------------------------------------------------
    # Krok 1: kalendar
    # ------------------------------------------------------------------
    def _on_load_calendar(self) -> None:
        try:
            year = int(self.year_var.get())
        except ValueError:
            messagebox.showerror("f1viz", "rok musi byt cislo")
            return
        if year < 1950:
            messagebox.showerror("f1viz", "rocnik mimo rozsahu F1")
            return

        self.status_var.set(f"nacitavam kalendar {year} ...")
        self.btn_calendar.state(["disabled"])
        self._run_async(get_event_schedule, self._calendar_loaded, year)

    def _calendar_loaded(self, schedule) -> None:
        self._schedule = schedule.sort_values("RoundNumber")
        labels = [
            f"{int(r.RoundNumber):>2}. {r.EventName}"
            for r in self._schedule.itertuples()
        ]
        self.event_combo["values"] = labels
        self.event_combo.state(["!disabled", "readonly"])
        self.btn_calendar.state(["!disabled"])
        self.status_var.set(f"kalendar nacitany — {len(labels)} zavodov")

    # ------------------------------------------------------------------
    # Krok 2: zavod -> dostupne session
    # ------------------------------------------------------------------
    def _on_event_selected(self, _evt=None) -> None:
        idx = self.event_combo.current()
        if idx < 0 or self._schedule is None:
            return
        self._event = self._schedule.iloc[idx]

        codes = []
        for i in range(1, 6):
            label = self._event.get(f"Session{i}")
            if isinstance(label, str) and label:
                codes.append(SESSION_LABEL_TO_CODE.get(label, label.upper()[:2]))

        self.session_combo["values"] = codes
        self.session_combo.state(["!disabled", "readonly"])
        if codes:
            self.session_combo.current(0)
        self.btn_session.state(["!disabled"])
        self.status_var.set(f"zavod: {self._event['EventName']}")

    # ------------------------------------------------------------------
    # Krok 3: nacitanie session -> zoznam jazdcov
    # ------------------------------------------------------------------
    def _on_load_session(self) -> None:
        if self._event is None or not self.session_var.get():
            return
        year = int(self.year_var.get())
        round_no = int(self._event["RoundNumber"])
        ident = self.session_var.get()

        self.status_var.set(
            f"nacitavam {self._event['EventName']} {ident} ... (prve stiahnutie trva dlhsie)"
        )
        self.btn_session.state(["disabled"])
        self._run_async(load_session, self._session_loaded, year, round_no, ident)

    def _session_loaded(self, session) -> None:
        self._session = session
        drivers = sorted(session.laps["Driver"].unique())
        if len(drivers) < 2:
            self.status_var.set("chyba: menej ako dvaja jazdci s kolami")
            self.btn_session.state(["!disabled"])
            return

        for combo in (self.drv1_combo, self.drv2_combo):
            combo["values"] = drivers
            combo.state(["!disabled", "readonly"])
        self.drv1_combo.current(0)
        self.drv2_combo.current(1)

        self.btn_session.state(["!disabled"])
        self.btn_compare.state(["!disabled"])
        self.status_var.set(f"session nacitana — {len(drivers)} jazdcov s kolami")

    # ------------------------------------------------------------------
    # Krok 4: porovnanie
    # ------------------------------------------------------------------
    def _on_compare(self) -> None:
        ref, cmp_ = self.drv1_var.get(), self.drv2_var.get()
        if not ref or not cmp_:
            return
        if ref == cmp_:
            messagebox.showerror("f1viz", "potrebujem dvoch roznych jazdcov")
            return

        self.status_var.set(f"pocitam {ref} vs {cmp_} ...")
        self.btn_compare.state(["disabled"])
        self._run_async(self._compute_comparison, self._comparison_ready, ref, cmp_)

    def _compute_comparison(self, ref_code: str, cmp_code: str):
        def fastest(code: str):
            laps = self._session.laps.pick_drivers(code)
            if laps.empty:
                raise ValueError(f"'{code}' nema v tejto session kola")
            lap = laps.pick_fastest()
            if lap is None or lap.empty:
                raise ValueError(f"'{code}' nema platne meratelne kolo")
            return lap

        ref = fastest(ref_code)
        cmp_ = fastest(cmp_code)
        delta_df = lap_delta(ref, cmp_)
        sectors = sector_matrix(self._session.laps).round(3)
        return ref_code, cmp_code, delta_df, sectors

    def _comparison_ready(self, payload) -> None:
        ref_code, cmp_code, delta_df, sectors = payload
        self.btn_compare.state(["!disabled"])
        self.status_var.set(f"hotovo: {ref_code} vs {cmp_code}")

        self.ax.clear()
        plots.plot_delta(delta_df, ref_code, cmp_code, ax=self.ax)
        self.canvas.draw()

        self.table.delete(*self.table.get_children())
        cols = ["Driver", *sectors.columns]
        self.table["columns"] = cols
        self.table.column("Driver", width=70, anchor="w")
        self.table.heading("Driver", text="Driver")
        for c in sectors.columns:
            self.table.heading(c, text=c)
            self.table.column(c, width=95, anchor="e")
        for driver, row in sectors.iterrows():
            self.table.insert("", "end", values=[driver, *(f"{v:.3f}" for v in row)])


def main() -> int:
    app = F1VizApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
