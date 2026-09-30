"""Monte Carlo of the TRUE chain (diplexer + preselector as one network): IIP2_eff and
HF-band desense, tolerances on both filters (same distributions as the block Monte Carlos)."""
import sys, os, json
import numpy as np
import dip_presel as D
from netsolve import sparams, db, loss_worst
import preselector as P
from noise_budget import desense, DESENSE_MAX

F = np.logspace(np.log10(0.3e6), np.log10(200e6), 900)


def perturb(el, rng):
    out = []
    for k, a, b, v in el:
        if k == "Lcc":
            L, R1, R2, C, kk = v
            v = (L * (1 + rng.uniform(-.02, .02)), R1, R2 * (1 + rng.uniform(-.1, .1)),
                 C * (1 + rng.uniform(-.1, .1)), kk * (1 + rng.uniform(-.1, .1)))
        elif k == "Creal":
            C, esl, esr = v
            C = C + max(abs(C * rng.uniform(-.02, .02)), abs(rng.uniform(-.1e-12, .1e-12))) * rng.choice([-1, 1])
            v = (C, esl * (1 + rng.uniform(-.2, .2)), esr)
        elif k == "TL2":                                  # air-core inductor: L tolerance via Z0 (G = 2 %)
            Zc, el_, f0 = v
            v = (Zc * (1 + rng.uniform(-.02, .02)), el_, f0)
        elif k == "R" and v < 5.0:                        # air-core series loss R2
            v = v * (1 + rng.uniform(-.1, .1))
        elif k == "C" and v < 2e-12:                      # pads / trace sections
            v = v * (1 + rng.uniform(-.2, .2))
        elif k == "L" and v < 2e-9:                       # vias / trace sections
            v = v * (1 + rng.uniform(-.2, .2))
        out.append((k, a, b, v))
    return out


if __name__ == "__main__":
    band = sys.argv[1]; runs = int(sys.argv[2]); src = sys.argv[3] if len(sys.argv) > 3 else None
    fl, fh = P.BANDS[band]
    el, ports, nn = D.combined(band, src)
    fb = np.linspace(fl, fh, 31)
    # presel-only loss for desense: the noise model already includes diplexer loss separately
    Sref = D.DIP.sim(D.DIP_L, D.DIP_C, fb)
    rng = np.random.default_rng(5); iip2, des = [], []
    for i in range(runs + 1):
        e = el if i == 0 else perturb(el, rng)
        S = sparams(e, ports, F, nn)
        S2 = np.zeros((len(F), 2, 2), complex); S2[:, 1, 0] = S[:, 1, 0]
        m = P.iip2_map(S2, F, fl, fh)
        iip2.append(min(m["sum"]["IIP2_eff_dBm"], m["diff"]["IIP2_eff_dBm"]))
        Sb = sparams(e, ports, fb, nn)
        presel_part = -db(Sb[:, 1, 0]) - (-db(Sref[:, 1, 0]))     # chain loss minus nominal diplexer loss
        des.append(float(desense(fb / 1e6, presel_part).max()))
    iip2 = np.array(iip2); des = np.array(des)
    out = {"band": band, "runs": runs, "nominal_iip2": round(float(iip2[0]), 1), "nominal_desense": round(float(des[0]), 2),
           "iip2_p1": round(float(np.percentile(iip2[1:], 1)), 1), "iip2_min": round(float(iip2[1:].min()), 1),
           "fail_iip2_%": round(100 * float(np.mean(iip2[1:] < 60)), 1),
           "desense_p99": round(float(np.percentile(des[1:], 99)), 2),
           "fail_desense_%": round(100 * float(np.mean(des[1:] > DESENSE_MAX[band])), 1)}
    json.dump(out, open(os.path.join(D.HERE, f"mc_chain_{band}" + ('_' + os.path.splitext(os.path.basename(src))[0] if src else '') + '.json'), "w"), indent=1)
    print(json.dumps(out))
