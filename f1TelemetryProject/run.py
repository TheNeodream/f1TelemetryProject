from f1viz.acquisition import init_cache, load_session
from f1viz.analysis import sector_matrix, lap_delta
from f1viz import plots
import matplotlib.pyplot as plt

init_cache()
s = load_session(2026, "Belgium", "FP3")

# 1. Kde sa reálne stráca čas — po sektoroch
print(sector_matrix(s.laps).round(3).to_string())

# 2. Delta medzi dvoma jazdcami na ich najrýchlejšom kole
plots.setup()
a = s.laps.pick_drivers("ANT").pick_fastest()
b = s.laps.pick_drivers("RUS").pick_fastest()
plots.plot_delta(lap_delta(a, b), "ANT", "RUS")
plt.tight_layout()
plt.show()