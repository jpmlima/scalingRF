"""Re-optimise a preselector band INSIDE the real chain (diplexer + preselector as one network).
Inductors: current parts and their nearest neighbours; capacitors re-optimised, snapped to E24.
Objective: IIP2_eff on the chain S21, desense from the chain loss minus nominal diplexer loss,
return loss at the antenna in the band."""
import sys, os, json, itertools
import numpy as np
from scipy.optimize import least_squares
import dip_presel as D
import preselector_ell as E, preselector as P
from netsolve import sparams, db, rl_worst
from noise_budget import budget_curve, desense, DESENSE_MAX

band = sys.argv[1]; GOAL = float(sys.argv[2]) if len(sys.argv) > 2 else 63.0
LIB = sys.argv[3] if len(sys.argv) > 3 else "0805HP"          # inductor family: 0805HP or SQ
from coilcraft_sq import SQ
fl, fh = P.BANDS[band]
F_OPT = np.logspace(np.log10(0.3e6), np.log10(200e6), 280)
inb = (F_OPT >= fl) & (F_OPT <= fh)
DIP_IN = D.DIP.sim(D.DIP_L, D.DIP_C, F_OPT)[:, 1, 0]
BUD = budget_curve(F_OPT[inb], DESENSE_MAX[band])
_src = os.path.join(D.HERE, f"chain_{band}.json")
if not os.path.exists(_src): _src = os.path.join(D.HERE, "..", "preselector", f"ell_{band}.json")
j0 = json.load(open(_src))
v0 = np.array(j0["values"]); parts0 = j0["inductors"]


def chain(v, parts, F):
    el_d, ports_d, nn_d = D.DIP.build_real(D.DIP_L, D.DIP_C)
    (com, _), (lp, _), (hp, _) = ports_d
    el_p, ports_p, nn_p = E.build(v, ("parts", parts))
    (p_in, _), (p_out, _) = ports_p
    off = nn_d - 2
    rm = lambda n: 0 if n == 0 else (lp if n == p_in else n + off)
    el = list(el_d) + [(k, rm(a), rm(b), x) for k, a, b, x in el_p]
    return sparams(el, [(com, 50.0), (rm(p_out), 50.0), (hp, 50.0)], F, nn_p + off)


def resid(x, parts):
    v = v0.copy(); v[~E.IS_L] = np.exp(x); v[E.IS_L] = [E.Lval(n) for n in parts]
    S = chain(v, parts, F_OPT)
    A = -db(S[:, 1, 0]); presel = A - (-db(DIP_IN))
    r = list(1.0 * np.maximum(0, presel[inb] - (BUD - 0.2))) + list(0.1 * presel[inb])
    r += list(0.3 * np.maximum(0, 13 - (-db(S[inb, 0, 0]))))
    Ai = lambda f: np.interp(f, F_OPT, A)
    for fp in np.linspace(fl, fh, 15):
        f2 = np.linspace(F_OPT[0], fp / 2, 60)
        es = (P.IIP2_LNA + Ai(fp - f2) + Ai(f2) - Ai(fp)).min()
        f2 = np.linspace(F_OPT[0], F_OPT[-1] - fp, 120)
        ed = (P.IIP2_LNA + Ai(fp + f2) + Ai(f2) - Ai(fp)).min()
        r += [0.5 * max(0, GOAL - es), 0.5 * max(0, GOAL - ed)]
    return np.array(r)


def score(v, parts):
    F = np.logspace(np.log10(0.3e6), np.log10(200e6), 900)
    S = chain(v, parts, F)
    S2 = np.zeros((len(F), 2, 2), complex); S2[:, 1, 0] = S[:, 1, 0]
    m = P.iip2_map(S2, F, fl, fh); ip = min(m["sum"]["IIP2_eff_dBm"], m["diff"]["IIP2_eff_dBm"])
    fb = np.linspace(fl, fh, 31); Sb = chain(v, parts, fb)
    dref = D.DIP.sim(D.DIP_L, D.DIP_C, fb)[:, 1, 0]
    ds = float(desense(fb / 1e6, -db(Sb[:, 1, 0]) + db(dref)).max())
    return ip, ds, rl_worst(Sb[:, 0, 0]), m


lo = np.log(np.full((~E.IS_L).sum(), 1e-12)); hi = np.log(np.full((~E.IS_L).sum(), 2.2e-9))
pool = list(SQ) if LIB == "SQ" else list(P.L_AVAIL)
cands = [sorted(pool, key=lambda n: abs(np.log(E.Lval(n) / E.Lval(p))))[:2] for p in parts0]
best = None
for combo in itertools.product(*cands):
    x0 = np.clip(np.log(v0[~E.IS_L]), lo + 1e-6, hi - 1e-6)
    sol = least_squares(resid, x0, args=(combo,), bounds=(lo, hi), max_nfev=10)
    v = v0.copy(); v[~E.IS_L] = [P.snapE24(c) for c in np.exp(sol.x)]; v[E.IS_L] = [E.Lval(n) for n in combo]
    ip, ds, rl, m = score(v, combo)
    s = ip - 5 * max(0, ds - DESENSE_MAX[band]) - 0.5 * max(0, 12 - rl)
    if best is None or s > best[0]: best = (s, combo, v, ip, ds, rl, m)
_, combo, v, ip, ds, rl, m = best
out = {"band": band, "goal": GOAL, "IIP2_eff_chain": ip, "desense_chain": round(ds, 2), "RL_antenna_in_band": round(rl, 1),
       "worst_pairs": m, "inductors": list(combo),
       "caps_pF": {n: round(float(c) * 1e12, 1) for n, c in zip(E.NAMES, v) if not n.startswith("L")},
       "values": [float(x) for x in v]}
json.dump(out, open(os.path.join(D.HERE, f"chain_{band}{'_SQ' if LIB == 'SQ' else ''}.json"), "w"), indent=1)
print(json.dumps({k: out[k] for k in out if k not in ("values", "worst_pairs")}))
