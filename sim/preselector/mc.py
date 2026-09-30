"""Monte Carlo on the rev 1 elliptic designs.
Tolerances: L +-2 %, inductor parasitic C +-10 %, inductor loss terms (R2, k) +-10 %,
caps +-2 % or +-0.1 pF (larger), board parasitics +-20 %.
Metrics: worst IIP2_eff (preselector only, and preselector + diplexer LP arm),
worst desense, worst RL."""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "diplexer"))
import preselector_ell as E, preselector as P
from noise_budget import desense, DESENSE_MAX
from netsolve import db
import real_parts as DIP

F = np.logspace(np.log10(0.1e6), np.log10(150e6), 1500)
DIP_L = ('0805HP-271', '0805HP-271', '0805HP-56N', '0805HP-82N', '0805HP-101')
DIP_C = np.array([82, 62, 33, 30, 110]) * 1e-12
S_dip = DIP.sim(DIP_L, DIP_C, F)[:, 1, 0]            # diplexer rev 2, LP arm


def worst_iip2(s21, fl, fh):
    S = np.zeros((len(F), 2, 2), complex); S[:, 1, 0] = s21
    m = P.iip2_map(S, F, fl, fh)
    return min(m["sum"]["IIP2_eff_dBm"], m["diff"]["IIP2_eff_dBm"])


def metrics(v, parts, fl, fh, band):
    S = E.sim(v, ("parts", parts), F)
    fb = np.linspace(fl, fh, 41); Sb = E.sim(v, ("parts", parts), fb)
    return {"iip2_presel": worst_iip2(S[:, 1, 0], fl, fh),
            "iip2_with_diplexer": worst_iip2(S[:, 1, 0] * S_dip, fl, fh),
            "desense": float(desense(fb / 1e6, -db(Sb[:, 1, 0])).max()),
            "rl": float(-db(Sb[:, 0, 0]).max())}


if __name__ == "__main__":
    band = sys.argv[1]; runs = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    fl, fh = P.BANDS[band]
    j = json.load(open(os.path.join(HERE, f"ell_{band}.json")))
    v0 = np.array(j["values"]); parts = j["inductors"]
    nom = metrics(v0, parts, fl, fh, band)
    rng = np.random.default_rng(11)
    base_parts = {n: P.PARTS[n] for n in set(parts)}; base_par = dict(P.PAR)
    res = []
    for _ in range(runs):
        for n, (L, R1, R2, C, k, up) in base_parts.items():
            P.PARTS[n] = (L * (1 + rng.uniform(-.02, .02)), R1, R2 * (1 + rng.uniform(-.1, .1)),
                          C * (1 + rng.uniform(-.1, .1)), k * (1 + rng.uniform(-.1, .1)), up)
        for key in ("C_ESL", "pad_C", "via_L"):
            P.PAR[key] = base_par[key] * (1 + rng.uniform(-.2, .2))
        v = v0.copy()
        for i in np.where(~E.IS_L)[0]:
            c = v0[i]; v[i] = c + max(abs(c * rng.uniform(-.02, .02)), abs(rng.uniform(-.1e-12, .1e-12))) * rng.choice([-1, 1])
        res.append(metrics(v, parts, fl, fh, band))
    P.PARTS.update(base_parts); P.PAR.update(base_par)
    arr = {k: np.array([r[k] for r in res]) for k in res[0]}
    out = {"band": band, "runs": runs, "nominal": {k: round(x, 2) for k, x in nom.items()},
           "iip2_presel_p1": round(float(np.percentile(arr["iip2_presel"], 1)), 1),
           "iip2_with_diplexer_p1": round(float(np.percentile(arr["iip2_with_diplexer"], 1)), 1),
           "desense_p99": round(float(np.percentile(arr["desense"], 99)), 2),
           "rl_p1": round(float(np.percentile(arr["rl"], 1)), 1),
           "fail_iip2_presel_%": round(100 * float(np.mean(arr["iip2_presel"] < 60)), 1),
           "fail_iip2_with_diplexer_%": round(100 * float(np.mean(arr["iip2_with_diplexer"] < 60)), 1),
           "fail_desense_%": round(100 * float(np.mean(arr["desense"] > DESENSE_MAX[band])), 1)}
    json.dump(out, open(os.path.join(HERE, f"mc_{band}.json"), "w"), indent=1)
    print(json.dumps(out))
