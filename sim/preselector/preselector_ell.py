"""
Preselector rev 1 — elliptic sections.

Per band, 4 inductors + 10 capacitors:
  LP: C1 shunt | (L2 || Cz2) series | C3 shunt | (L4 || Cz4) series | C5 shunt
  HP: C6 series | (L7 + Cz7) shunt | C8 series | (L9 + Cz9) shunt | C10 series
Parallel/series resonators put transmission zeros just above the band (near 2*fl)
and just below it (near fh-fl), where the critical IM2 tone pairs live.

The optimiser works directly on the metric: worst effective IIP2 over all tone pairs
(target +62 dBm = spec +60 with 2 dB margin) and the per-band loss budget derived
from the noise analysis (rev 0 README).
"""
import sys, os, json, itertools
import numpy as np
from scipy.optimize import least_squares
import preselector as P                     # rev 0 helpers: Net, PAR, sim tools, iip2_map, PARTS
from netsolve import sparams, db
from coilcraft_sq import SQ
from noise_budget import budget_curve, DESENSE_MAX

LOSS_BUDGET = {"B1": 6.0, "B2": 4.0, "B3": 2.0}
IIP2_GOAL = float(os.environ.get("IIP2_GOAL", 62.0))
RL_MIN = 14.0
# value order: C1 L2 Cz2 C3 L4 Cz4 C5 C6 L7 Cz7 C8 L9 Cz9 C10
NAMES = ["C1", "L2", "Cz2", "C3", "L4", "Cz4", "C5", "C6", "L7", "Cz7", "C8", "L9", "Cz9", "C10"]
IS_L = np.array([n.startswith("L") for n in NAMES])


def build(v, lmodel, parasitic=True):
    net = P.Net(); p1 = net.node()
    def gnd():
        if not parasitic: return 0
        g = net.node(); net.add("L", g, 0, P.PAR["via_L"], pads=False); return g
    def cap(a, b, c):
        if parasitic: net.add("Creal", a, b, (c, P.PAR["C_ESL"], P.PAR["C_ESR"]))
        else: net.add("C", a, b, c)
    li = iter(range(4))
    def ind(a, b, L):
        i = next(li)
        if lmodel[0] == "Q": net.add("Lreal", a, b, (L, lmodel[1], 0.0, 0.0))
        elif lmodel[1][i] in SQ:                  # air-core, transmission-line model (Doc 836-2)
            p = SQ[lmodel[1][i]]
            m1 = net.node(); m2 = net.node()
            net.add("R", a, m1, p["R2"]); net.add("TL2", m1, b, (p["Z0"], p["EL"], p["F0"]), pads=False)
            net.add("R", a, m2, p["R1"], pads=False); net.add("C", m2, b, p["C"], pads=False)
        else:
            Lp, R1, R2, C, k, _ = P.PARTS[lmodel[1][i]]; net.add("Lcc", a, b, (Lp, R1, R2, C, k))
    C1, L2, Cz2, C3, L4, Cz4, C5, C6, L7, Cz7, C8, L9, Cz9, C10 = v
    x = p1
    cap(x, gnd(), C1)
    y = net.node(); ind(x, y, L2); cap(x, y, Cz2); x = y
    cap(x, gnd(), C3)
    y = net.node(); ind(x, y, L4); cap(x, y, Cz4); x = y
    cap(x, gnd(), C5)
    y = net.node(); cap(x, y, C6); x = y
    m = net.node(); ind(x, m, L7); cap(m, gnd(), Cz7)
    y = net.node(); cap(x, y, C8); x = y
    m = net.node(); ind(x, m, L9); cap(m, gnd(), Cz9)
    y = net.node(); cap(x, y, C10); p2 = y
    if parasitic:
        for nd, c in net.pads.items(): net.el.append(("C", nd, 0, c * P.PAR["pad_C"]))
    return net.el, [(p1, 50.0), (p2, 50.0)], net.n


def sim(v, lmodel, F, parasitic=True):
    el, ports, nn = build(v, lmodel, parasitic)
    return sparams(el, ports, F, nn)


F_OPT = np.logspace(np.log10(0.3e6), np.log10(150e6), 260)
BUDGET = {b: budget_curve(F_OPT[(F_OPT >= fl) & (F_OPT <= fh)], DESENSE_MAX[b]) for b, (fl, fh) in P.BANDS.items()}


def start(fl, fh):
    v0 = P.start(fl, fh)                      # rev 0 Chebyshev values [C1,L2,C3,L4,C5,C6,L7,C8,L9,C10]
    C1, L2, C3, L4, C5, C6, L7, C8, L9, C10 = v0
    fz_hi = [2.05 * fl, 2.5 * fl]             # LP zeros above band
    fz_lo = [0.95 * (fh - fl), 0.6 * (fh - fl)]  # HP zeros below band
    Cz2 = 1 / ((2 * np.pi * fz_hi[0]) ** 2 * L2); Cz4 = 1 / ((2 * np.pi * fz_hi[1]) ** 2 * L4)
    Cz7 = 1 / ((2 * np.pi * fz_lo[0]) ** 2 * L7); Cz9 = 1 / ((2 * np.pi * fz_lo[1]) ** 2 * L9)
    return np.array([C1, L2, Cz2, C3, L4, Cz4, C5, C6, L7, Cz7, C8, L9, Cz9, C10])


def resid(x, band, lmodel, fixed=None):
    fl, fh = P.BANDS[band]
    v = np.exp(x)
    if fixed is not None:
        full = np.array(fixed, float); full[~IS_L] = v; v = full
    S = sim(v, lmodel, F_OPT)
    A = -db(S[:, 1, 0]); RL = -db(S[:, 0, 0])
    inb = (F_OPT >= fl) & (F_OPT <= fh)
    r = list(1.0 * np.maximum(0, A[inb] - (BUDGET[band] - 0.2)))        # desense-derived budget, 0.2 dB margin
    r += list(0.15 * A[inb])                                           # and prefer lower loss
    r += list(0.3 * np.maximum(0, RL_MIN + 1 - RL[inb]))
    Ai = lambda f: np.interp(f, F_OPT, A)
    for fp in np.linspace(fl, fh, 15):
        f2 = np.linspace(F_OPT[0], fp / 2, 60)
        e_sum = (P.IIP2_LNA + Ai(fp - f2) + Ai(f2) - Ai(fp)).min()
        f2 = np.linspace(F_OPT[0], F_OPT[-1] - fp, 120)
        e_dif = (P.IIP2_LNA + Ai(fp + f2) + Ai(f2) - Ai(fp)).min()
        r += [0.5 * max(0, IIP2_GOAL - e_sum), 0.5 * max(0, IIP2_GOAL - e_dif)]
    return np.array(r)


def run(band):
    fl, fh = P.BANDS[band]
    x0 = np.log(start(fl, fh))
    lo, hi = np.log(np.where(IS_L, 10e-9, 1e-12)), np.log(np.where(IS_L, 820e-9, 2.2e-9))
    x0 = np.clip(x0, lo + 1e-6, hi - 1e-6)
    solA = least_squares(resid, x0, args=(band, ("Q", 30.0)), bounds=(lo, hi), max_nfev=80)
    vA = np.exp(solA.x)
    cands = []
    for L in vA[IS_L]:
        cands.append(sorted(P.L_AVAIL, key=lambda n: abs(np.log(P.PARTS[n][0] / L)))[:2])
    F = np.logspace(np.log10(0.1e6), np.log10(150e6), 2500)
    best = None
    for combo in itertools.product(*cands):
        fixed = vA.copy(); fixed[IS_L] = [P.PARTS[n][0] for n in combo]
        xc = np.log(vA[~IS_L])
        sol = least_squares(resid, xc, args=(band, ("parts", combo), fixed),
                            bounds=(lo[~IS_L], hi[~IS_L]), max_nfev=12)
        v = fixed.copy(); v[~IS_L] = [P.snapE24(c) for c in np.exp(sol.x)]
        S = sim(v, ("parts", combo), F)
        ev = P.evaluate(S, F, fl, fh); m = P.iip2_map(S, F, fl, fh)
        worst = min(m["sum"]["IIP2_eff_dBm"], m["diff"]["IIP2_eff_dBm"])
        fb = np.linspace(fl, fh, 41); Sb = sim(v, ("parts", combo), fb)
        over = float(np.max(-db(Sb[:, 1, 0]) - budget_curve(fb, DESENSE_MAX[band])))
        score = worst - 5 * max(0, over) - max(0, RL_MIN - ev["RL_worst_dB"])
        if best is None or score > best[0]:
            best = (score, combo, v, ev, m)
    _, combo, v, ev, m = best
    out = {"band_MHz": [fl / 1e6, fh / 1e6], "loss_budget_dB": LOSS_BUDGET[band],
           **{k: round(x, 2) for k, x in ev.items()}, "IIP2": m,
           "inductors": list(combo),
           "caps_pF": {n: round(float(c) * 1e12, 1) for n, c in zip(NAMES, v) if not n.startswith("L")},
           "values": [float(x) for x in v]}
    json.dump(out, open(os.path.join(P.HERE, f"ell_{band}.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    o = run(sys.argv[1])
    print(json.dumps({k: o[k] for k in o if k != "values"}))


def Lval(name):
    """Nominal inductance of a part from either library."""
    return SQ[name]["L"] if name in SQ else P.PARTS[name][0]
