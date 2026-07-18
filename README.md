# f1viz — kostra

Styri vrstvy, ktore sa nesmu miesat:

    acquisition.py   vie o FastF1. Nic ine o nom nevie.
    (model)          kanonicky tvar dat — zatial staci Laps/Telemetry
    analysis.py      ciste funkcie. Ziadny plot, ziadny print.
    plots.py         hlupa vrstva. Nic nepocita.

## Start

    pip install -r requirements.txt
    python inspect_session.py 2026 Belgium FP3

`inspect_session.py` nekresli nic. Zisti, ci su data uplne
a ktore kanaly telemetrie realne existuju.

## Znama pasca 2026

Kanaly pohonnej jednotky (stav baterie, nasadenie MGU-K, override)
NIE SU v oficialnom timing feede. `analysis.implied_deployment()`
ich len nepriamo odhaduje z dv/dt na rovinke. Je to hypoteza,
nie meranie. Kto to prezentuje ako meranie, klame.
