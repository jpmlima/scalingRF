"""
scalingRF — HF LNA-path preselector: three sub-octave band-pass filters
(10-17, 17-29, 29-49 MHz), 50 ohm, each a 5th-order LP (shunt-C first) cascaded
with a 5th-order HP (series-C first): 4 inductors + 6 capacitors per band.

Metric: effective IIP2 of preselector + LTC6433-15 for every tone pair whose
2nd-order product (f1+f2 or |f1-f2|) lands in the band:
    IIP2_eff = IIP2_LNA + A(f1) + A(f2) - A(fp)   (A = preselector loss, dB; the product
    is generated after the filter, so it is referred back to the antenna through the in-band loss at fp)
and the equivalent "maximum level of two equal stations before their IM2 product
exceeds the 2.4 kHz MDS":  P_max = (IIP2_eff + MDS) / 2.

Stages: A ideal (constant-Q inductor) optimisation -> B inductors snapped to
real Coilcraft 0805HP parts, caps re-optimised with the real models and board
parasitics, caps snapped to E24 -> C Monte Carlo.
"""
import sys, os, json, itertools
import numpy as np
from scipy.optimize import least_squares
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "diplexer"))
from netsolve import sparams, db                         # validated solver
from coilcraft_0805hp import PARTS                        # manufacturer models

Z0 = 50.0
BANDS = {"B1": (10e6, 17e6), "B2": (17e6, 29e6), "B3": (29e6, 49e6)}

# ---------------- spec ----------------
IL_MAX = 1.0            # dB, passband, real parts
RL_MIN = 14.0           # dB, passband
REJ_TARGET = 25.0       # dB at 2*fl and at fh-fl (22 dB needed for IIP2_eff >= +60 dBm, +3 margin)
IIP2_LNA = 38.0         # dBm, LTC6433-15, estimated from HD2 (sim/hf_rx rev 2)
MDS = -131.0            # dBm, 2.4 kHz, LNA mode NF ~9 dB
IIP2_EFF_TARGET = 60.0  # dBm

# ---------------- board parasitics (same as diplexer) ----------------
PAR = {"C_ESL": 0.35e-9, "C_ESR": 0.15, "pad_C": 0.05e-12, "via_L": 0.4e-9}

E24 = np.array([1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
                3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1])
L_AVAIL = sorted(PARTS, key=lambda n: PARTS[n][0])


def snapE24(v):
    e = np.floor(np.log10(v)); m = v / 10 ** e
    c = np.concatenate([E24, [10.0]])
    return c[np.argmin(np.abs(np.log(c / m)))] * 10 ** e


# ---------------- netlist ----------------
class Net:
    def __init__(self): self.el, self.n, self.pads = [], 1, {}
    def node(self): self.n += 1; return self.n - 1
    def add(self, k, a, b, v, pads=True):
        self.el.append((k, a, b, v))
        if pads:
            for x in (a, b):
                if x: self.pads[x] = self.pads.get(x, 0) + 1


def build(vals, lmodel, parasitic):
    """vals: [C1, L2, C3, L4, C5 | C6, L7, C8, L9, C10]
    LP: C1 shunt, L2 series, C3 shunt, L4 series, C5 shunt
    HP: C6 series, L7 shunt, C8 series, L9 shunt, C10 series
    lmodel: ('Q', Q) constant-Q ideal-ish, or ('parts', [names for L2,L4,L7,L9])."""
    net = Net(); p1 = net.node()

    def gnd():
        if not parasitic: return 0
        g = net.node(); net.add("L", g, 0, PAR["via_L"], pads=False); return g

    def cap(a, b, c):
        if parasitic: net.add("Creal", a, b, (c, PAR["C_ESL"], PAR["C_ESR"]))
        else: net.add("C", a, b, c)

    li = iter(range(4))
    def ind(a, b, L):
        i = next(li)
        if lmodel[0] == "Q":
            net.add("Lreal", a, b, (L, lmodel[1], 0.0, 0.0))
        else:
            Lp, R1, R2, C, k, _ = PARTS[lmodel[1][i]]
            net.add("Lcc", a, b, (Lp, R1, R2, C, k))

    C1, L2, C3, L4, C5, C6, L7, C8, L9, C10 = vals
    x = p1
    cap(x, gnd(), C1); y = net.node(); ind(x, y, L2); x = y
    cap(x, gnd(), C3); y = net.node(); ind(x, y, L4); x = y
    cap(x, gnd(), C5)
    y = net.node(); cap(x, y, C6); x = y
    ind(x, gnd(), L7)
    y = net.node(); cap(x, y, C8); x = y
    ind(x, gnd(), L9)
    y = net.node(); cap(x, y, C10); p2 = y
    if parasitic:
        for nd, c in net.pads.items(): net.el.append(("C", nd, 0, c * PAR["pad_C"]))
    return net.el, [(p1, Z0), (p2, Z0)], net.n


def sim(vals, lmodel, F, parasitic=True):
    el, ports, nn = build(vals, lmodel, parasitic)
    return sparams(el, ports, F, nn)


# ---------------- starting point: Chebyshev 0.1 dB, g = 1.1468, 1.3712, 1.9750, 1.3712, 1.1468 ----------------
G5 = [1.1468, 1.3712, 1.9750, 1.3712, 1.1468]


def start(fl, fh):
    wl, wh = 2 * np.pi * fh * 1.06, 2 * np.pi * fl / 1.06   # LP corner above band, HP corner below
    lp = [G5[0] / (Z0 * wl), G5[1] * Z0 / wl, G5[2] / (Z0 * wl), G5[3] * Z0 / wl, G5[4] / (Z0 * wl)]
    hp = [1 / (G5[0] * Z0 * wh), Z0 / (G5[1] * wh), 1 / (G5[2] * Z0 * wh), Z0 / (G5[3] * wh), 1 / (G5[4] * Z0 * wh)]
    return np.array(lp + hp)


IS_L = np.array([0, 1, 0, 1, 0, 0, 1, 0, 1, 0], bool)


def grids(fl, fh):
    fin = np.linspace(fl, fh, 30)
    frej = np.array([fh - fl, 2 * fl, fl / 2, 2 * fh])
    return fin, frej


def resid(x, fl, fh, lmodel, fixed_L=None):
    v = np.exp(x)
    if fixed_L is not None:
        full = np.array(fixed_L, float); full[~IS_L] = v; v = full
    fin, frej = grids(fl, fh)
    S = sim(v, lmodel, np.concatenate([fin, frej]), parasitic=True)
    il = -db(S[:30, 1, 0]); rl = -db(S[:30, 0, 0]); rej = -db(S[30:, 1, 0])
    r = list(il)                                                  # minimise loss everywhere in band
    r += list(0.5 * np.maximum(0, RL_MIN + 2 - rl))
    r += list(1.0 * np.maximum(0, REJ_TARGET + 5 - rej[:2]))      # critical IM2 frequencies
    r += list(0.2 * np.maximum(0, 30 - rej[2:]))
    return np.array(r)


def evaluate(S, F, fl, fh):
    band = (F >= fl) & (F <= fh)
    Fi = lambda f: np.argmin(abs(F - f))
    return {"IL_worst_dB": float(-db(S[band, 1, 0]).min()),
            "IL_mid_dB": float(-db(S[Fi(np.sqrt(fl * fh)), 1, 0])),
            "RL_worst_dB": float(-db(S[band, 0, 0]).max()),
            "rej_at_fh_minus_fl_dB": float(-db(S[Fi(fh - fl), 1, 0])),
            "rej_at_2fl_dB": float(-db(S[Fi(2 * fl), 1, 0])),
            "rej_at_fl_over_2_dB": float(-db(S[Fi(fl / 2), 1, 0])),
            "rej_at_2fh_dB": float(-db(S[Fi(2 * fh), 1, 0]))}


def iip2_map(S, F, fl, fh):
    """Worst-case effective IIP2 over all tone pairs whose f1+f2 or |f1-f2| is in band."""
    A = -db(S[:, 1, 0])
    fp_grid = np.linspace(fl, fh, 41)
    worst = {"sum": (np.inf, None), "diff": (np.inf, None)}
    Ai = lambda f: np.interp(f, F, A)
    for fp in fp_grid:
        f2 = np.linspace(F[0], fp / 2, 200)                   # sum: f1 = fp - f2 >= f2
        e = IIP2_LNA + Ai(fp - f2) + Ai(f2) - Ai(fp)
        k = np.argmin(e)
        if e[k] < worst["sum"][0]: worst["sum"] = (float(e[k]), (float(fp - f2[k]), float(f2[k]), float(fp)))
        f2 = np.linspace(F[0], F[-1] - fp, 400)               # diff: f1 = fp + f2
        e = IIP2_LNA + Ai(fp + f2) + Ai(f2) - Ai(fp)
        k = np.argmin(e)
        if e[k] < worst["diff"][0]: worst["diff"] = (float(e[k]), (float(fp + f2[k]), float(f2[k]), float(fp)))
    out = {}
    for kind, (e, pair) in worst.items():
        out[kind] = {"IIP2_eff_dBm": round(e, 1),
                     "worst_pair_MHz": [round(p / 1e6, 2) for p in pair],
                     "P_max_each_dBm": round((e + MDS) / 2, 1),
                     "P_max_S9_plus_dB": round((e + MDS) / 2 + 73, 1)}
    return out


if __name__ == "__main__":
    F = np.unique(np.concatenate([np.logspace(np.log10(0.1e6), np.log10(150e6), 2500)]))
    results, designs = {}, {}
    only = sys.argv[1:] or list(BANDS)
    for bname, (fl, fh) in [(b, BANDS[b]) for b in only]:
        # --- A: constant-Q (Q=35) optimisation, all 10 values
        x0 = np.log(start(fl, fh))
        solA = least_squares(resid, x0, args=(fl, fh, ("Q", 35.0)), max_nfev=250)
        vA = np.exp(solA.x)
        # --- B: snap inductors to real parts (2 nearest each), re-optimise caps
        cand = []
        for L in vA[IS_L]:
            order = sorted(L_AVAIL, key=lambda n: abs(np.log(PARTS[n][0] / L)))
            cand.append(order[:2])
        best = None
        for combo in itertools.product(*cand):
            fixed = vA.copy(); fixed[IS_L] = [PARTS[n][0] for n in combo]
            sol = least_squares(resid, np.log(vA[~IS_L]), args=(fl, fh, ("parts", combo), fixed), max_nfev=60)
            v = fixed.copy(); v[~IS_L] = [snapE24(c) for c in np.exp(sol.x)]
            S = sim(v, ("parts", combo), F)
            ev = evaluate(S, F, fl, fh); m = iip2_map(S, F, fl, fh)
            score = min(m["sum"]["IIP2_eff_dBm"], m["diff"]["IIP2_eff_dBm"]) - 10 * max(0, ev["IL_worst_dB"] - IL_MAX)
            if best is None or score > best[0]:
                best = (score, combo, v, S, ev, m)
        _, combo, v, S, ev, m = best
        designs[bname] = {"inductors": list(combo),
                          "caps_pF": {k: round(float(c) * 1e12, 2) for k, c in zip(["C1", "C3", "C5", "C6", "C8", "C10"], v[~IS_L])},
                          "values": [float(x) for x in v]}
        results[bname] = {"band_MHz": [fl / 1e6, fh / 1e6], **{k: round(x, 2) for k, x in ev.items()}, "IIP2": m}
        print(bname, json.dumps(results[bname]), designs[bname]["inductors"], designs[bname]["caps_pF"])
    json.dump({"results": results, "designs": designs,
               "spec": {"IL_MAX": IL_MAX, "RL_MIN": RL_MIN, "REJ_TARGET": REJ_TARGET, "IIP2_LNA": IIP2_LNA,
                        "MDS": MDS, "IIP2_EFF_TARGET": IIP2_EFF_TARGET}},
              open(os.path.join(HERE, f"preselector_results_{'_'.join(only)}.json"), "w"), indent=1)
