"""1-dB edges and Monte Carlo for the best real-part candidates."""
import json, numpy as np
import diplexer as d
import real_parts as rp
from netsolve import db

rows = json.load(open("real_parts_search.json"))
F = np.logspace(np.log10(30e6), np.log10(100e6), 700)
FF = np.unique(np.concatenate([np.logspace(3, np.log10(6e9), 500), [30e6, 50e6, 70e6, 120e6]]))

def edges(S, F):
    il_lp = -db(S[:, 1, 0]); il_hp = -db(S[:, 2, 0])
    lp_edge = F[(il_lp <= 1.0) & (F < 60e6)].max()
    hp_edge = F[(il_hp <= 1.0) & (F > 60e6)].min()
    cross = F[np.argmin(np.abs(il_lp - il_hp))]
    return lp_edge, hp_edge, cross, il_lp[np.argmin(np.abs(F - cross))]

out = []
rng = np.random.default_rng(7)
base = dict(d.PAR)
for r in rows[:3]:
    Lp = tuple(r["L"]); Cs = np.array(r["C_pF"]) * 1e-12
    e = edges(rp.sim(Lp, Cs, F), F)
    # Monte Carlo: L tol +-2 % (0805HP G), C +-2 % / 0.1 pF, board parasitics +-20 %
    lpe, hpe, rlw, hpil_hi = [], [], [], []
    for _ in range(200):
        saved = {}
        for n in set(Lp):
            saved[n] = rp.PARTS[n]
            L, R1, R2, C, k, up = saved[n]
            rp.PARTS[n] = (L * (1 + rng.uniform(-.02, .02)), R1, R2, C * (1 + rng.uniform(-.1, .1)), k, up)
        Cm = np.array([max(c * (1 + rng.uniform(-.02, .02)), c + rng.uniform(-.1e-12, .1e-12)) for c in Cs])
        for key in ("C_ESL", "pad_C", "via_L"):
            d.PAR[key] = base[key] * (1 + rng.uniform(-.2, .2))
        S = rp.sim(Lp, Cm, F); ee = edges(S, F); lpe.append(ee[0]); hpe.append(ee[1])
        S2 = rp.sim(Lp, Cm, FF); c = d.check(S2, FF)
        rlw.append(min(c["rl_lp_worst_db"], c["rl_hp_worst_db"]))
        hb = (FF >= 100e6) & (FF <= 6e9); hpil_hi.append(float(-db(S2[hb, 2, 0]).min()))
        for n, v in saved.items(): rp.PARTS[n] = v
        d.PAR.update(base)
    item = {"L": Lp, "C_pF": r["C_pF"], "lp_1dB_edge_MHz": round(e[0] / 1e6, 1), "hp_1dB_edge_MHz": round(e[1] / 1e6, 1),
            "crossover_MHz": round(e[2] / 1e6, 1), "loss_at_crossover_dB": round(float(e[3]), 2),
            "mc_lp_1dB_edge_p1_MHz": round(np.percentile(lpe, 1) / 1e6, 1),
            "mc_hp_1dB_edge_p99_MHz": round(np.percentile(hpe, 99) / 1e6, 1),
            "mc_rl_worst_p1_dB": round(np.percentile(rlw, 1), 1),
            "mc_hp_il_100M_6G_p99_dB": round(np.percentile(hpil_hi, 99), 2)}
    out.append(item); print(item)
json.dump(out, open("real_parts_mc.json", "w"), indent=1)
