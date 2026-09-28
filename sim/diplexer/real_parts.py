"""Diplexer with real Coilcraft 0805HP inductor models (+ board parasitics).
Discrete search over available inductor values; capacitors optimised, then snapped to E24."""
import itertools, json, numpy as np
from scipy.optimize import least_squares
import diplexer as d
from netsolve import sparams, db
from coilcraft_0805hp import PARTS

d.N_LP = d.N_HP = 5
F_CHK = np.unique(np.concatenate([np.logspace(3, np.log10(6e9), 700), [30e6, 50e6, 70e6, 120e6]]))
F_OPT = np.concatenate([np.logspace(6, np.log10(50e6), 25), np.logspace(np.log10(70e6), np.log10(6e9), 35), [30e6, 120e6]])


def build_real(Lparts, Cvals):
    """Lparts: [L1,L3,L5,L2,L4] part names; Cvals: [C2,C4,C1,C3,C5]."""
    net = d.Net(); P = True
    com = net.node()
    def Lcc(a, b, name):
        L, R1, R2, C, k, _ = PARTS[name]; net.add("Lcc", a, b, (L, R1, R2, C, k))
    # LP: L1, C2, L3, C4, L5
    x = d.add_tl(net, com, P)
    y = net.node(); Lcc(x, y, Lparts[0]); x = y
    d.add_C(net, x, d.shunt_node(net, P), Cvals[0], P)
    y = net.node(); Lcc(x, y, Lparts[1]); x = y
    d.add_C(net, x, d.shunt_node(net, P), Cvals[1], P)
    y = net.node(); Lcc(x, y, Lparts[2]); p2 = y
    # HP: C1, L2, C3, L4, C5
    x = d.add_tl(net, com, P)
    y = net.node(); d.add_C(net, x, y, Cvals[2], P); x = d.add_tl(net, y, P)
    Lcc(x, d.shunt_node(net, P), Lparts[3])
    y = net.node(); d.add_C(net, x, y, Cvals[3], P); x = d.add_tl(net, y, P)
    Lcc(x, d.shunt_node(net, P), Lparts[4])
    y = net.node(); d.add_C(net, x, y, Cvals[4], P); p3 = y
    el, nn = net.finish(P)
    return el, [(com, 50.0), (p2, 50.0), (p3, 50.0)], nn


def sim(Lparts, Cvals, F):
    el, ports, nn = build_real(Lparts, Cvals)
    return sparams(el, ports, F, nn)


def resid(logc, Lparts):
    S = sim(Lparts, np.exp(logc), F_OPT)
    nl = 25; nh = 35
    r = list(-db(S[:nl, 1, 0])) + list(-db(S[nl:nl + nh, 2, 0]))          # minimise loss
    r += list(0.5 * np.maximum(0, db(S[:nl + nh, 0, 0]) + 15))
    r.append(0.2 * max(0, db(S[-2, 2, 0]) + 35)); r.append(0.2 * max(0, db(S[-1, 1, 0]) + 35))
    return np.array(r)


if __name__ == "__main__":
    res = json.load(open("results_n5.json"))
    lp = res["values"]["LP_snapped"]; hp = res["values"]["HP_snapped"]
    C0 = np.log([lp[1], lp[3], hp[0], hp[2], hp[4]])
    lo, hi = np.log([1e-12] * 5), np.log([330e-12] * 5)
    choices = [["0805HP-181", "0805HP-221", "0805HP-271"], ["0805HP-181", "0805HP-221", "0805HP-271"],
               ["0805HP-56N", "0805HP-82N"], ["0805HP-56N", "0805HP-82N"], ["0805HP-82N", "0805HP-101"]]
    rows = []
    for combo in itertools.product(*choices):
        sol = least_squares(resid, C0, args=(combo,), bounds=(lo, hi), max_nfev=150)
        Cs = np.array([d.snap(c, d.E24) for c in np.exp(sol.x)])
        c = d.check(sim(combo, Cs, F_CHK), F_CHK)
        rows.append({"L": combo, "C_pF": [round(x * 1e12, 2) for x in Cs], **c})
    rows.sort(key=lambda r: max(r["lp_il_worst_db"], r["hp_il_worst_db"]))
    json.dump(rows, open("real_parts_search.json", "w"), indent=1)
    for r in rows[:5]:
        print(r["L"], r["C_pF"], "LP %.2f HP %.2f RL %.1f/%.1f rej %.0f/%.0f %s" % (
            r["lp_il_worst_db"], r["hp_il_worst_db"], r["rl_lp_worst_db"], r["rl_hp_worst_db"],
            r["hp_rej_at_30MHz_db"], r["lp_rej_at_120MHz_db"], "PASS" if r["pass"] else "FAIL"))
    print("any pass:", any(r["pass"] for r in rows))
