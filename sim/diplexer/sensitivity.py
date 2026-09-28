"""Sensitivity of the 5th-order diplexer to the parasitics that the generic models guess."""
import json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import diplexer as d
from netsolve import db

d.N_LP = d.N_HP = 5
res = json.load(open("results_n5.json"))
lp = np.array(res["values"]["LP_snapped"]); hp = np.array(res["values"]["HP_snapped"])
F = np.unique(np.concatenate([np.logspace(3, np.log10(6e9), 800), [30e6, 120e6]]))
base = dict(d.PAR); out = {}

def run(conical=False):
    return d.check(d.simulate(lp, hp, F, parasitic=True, conical_first=conical), F)

out["baseline_wirewound"] = run(); out["baseline_conical"] = run(True)

# 1) Inductor parasitic capacitance, all inductors wirewound
sweep = []
for cp in [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6]:
    d.PAR.update(base); d.PAR["L_Cp"] = cp * 1e-12
    c = run(); sweep.append({"L_Cp_pF": cp, **c})
out["sweep_L_Cp"] = sweep

# 2) Via inductance
sweep = []
for lv in [0.2, 0.4, 0.8, 1.2]:
    d.PAR.update(base); d.PAR["via_L"] = lv * 1e-9
    sweep.append({"via_nH": lv, **run()})
out["sweep_via"] = sweep

# 3) Trace length between elements
sweep = []
for tl in [0.5, 1.5, 3.0, 5.0]:
    d.PAR.update(base); d.PAR["tl_len"] = tl * 1e-3
    sweep.append({"trace_mm": tl, **run()})
out["sweep_trace"] = sweep
d.PAR.update(base)

# 4) LP arm rejection at GHz (leakage into HF chain)
S = d.simulate(lp, hp, F, parasitic=True)
S_id = d.simulate(lp, hp, F)
g = F >= 100e6
out["lp_leak_min_rejection_100M_6G_db_parasitic"] = float(-db(S[g, 1, 0]).max())
out["lp_leak_freq_of_worst_hz"] = float(F[g][np.argmax(db(S[g, 1, 0]))])
out["lp_leak_min_rejection_100M_6G_db_ideal"] = float(-db(S_id[g, 1, 0]).max())

json.dump(out, open("sensitivity_n5.json", "w"), indent=2)

fig, ax = plt.subplots(figsize=(10, 4))
ax.semilogx(F, db(S_id[:, 1, 0]), "--", label="LP S21 ideal")
ax.semilogx(F, db(S[:, 1, 0]), label="LP S21 with parasitics")
ax.set_ylim(-100, 2); ax.grid(True, which="both", alpha=.3); ax.legend()
ax.set_title("LP (HF) arm: rejection up to 6 GHz"); ax.set_xlabel("Hz"); ax.set_ylabel("dB")
plt.tight_layout(); plt.savefig("lp_rejection_n5.png", dpi=130)

for k, v in out.items():
    if isinstance(v, list):
        print(k)
        for r in v:
            print("  ", {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in r.items()})
    else:
        print(k, v if not isinstance(v, dict) else {kk: (round(vv, 2) if isinstance(vv, float) else vv) for kk, vv in v.items()})
