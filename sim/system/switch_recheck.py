"""Re-check HF preselector desense with REAL pre-LNA switch losses.
Audit found the noise model counts one 0.3 dB switch before the LNA; the preselector band-select
switches (in and out) were never included. X = extra pre-LNA loss relative to that model."""
import os, json
import numpy as np
import dip_presel as D, mc_chain as MC
import preselector as P
from netsolve import sparams, db
from noise_budget import desense, DESENSE_MAX

SCEN = {"S0 as modelled (1 x 0.3 dB)": 0.0,
        "S1 current topology, PE42582-class (3 x 0.7 dB)": 3 * 0.7 - 0.3,
        "S2 merged SP4T in + SP3T out (2 x 0.7 dB)": 2 * 0.7 - 0.3,
        "S3 signal relays (2 x 0.1 dB, ASSUMED)": 2 * 0.1 - 0.3}
SRC = {"B1": None, "B2": None, "B3": os.path.join(D.HERE, "chain_B3_SQ.json")}

out = {}
for band, src in SRC.items():
    fl, fh = P.BANDS[band]
    el, ports, nn = D.combined(band, src)
    fb = np.linspace(fl, fh, 31)
    dref = D.DIP.sim(D.DIP_L, D.DIP_C, fb)[:, 1, 0]
    rng = np.random.default_rng(5)
    presel = []
    for i in range(101):
        e = el if i == 0 else MC.perturb(el, rng)
        Sb = sparams(e, ports, fb, nn)
        presel.append(-db(Sb[:, 1, 0]) + db(dref))
    out[band] = {}
    for name, X in SCEN.items():
        ds = np.array([desense(fb / 1e6, p + X).max() for p in presel])
        out[band][name] = {"nominal": round(float(ds[0]), 2), "p99": round(float(np.percentile(ds[1:], 99)), 2),
                           "fail_%": round(100 * float(np.mean(ds[1:] > DESENSE_MAX[band])), 1)}
json.dump(out, open(os.path.join(D.HERE, "switch_recheck.json"), "w"), indent=1)
for b, d in out.items():
    print(f"{b} (limit {DESENSE_MAX[b]} dB)")
    for k, v in d.items(): print(f"   {k:48s} nominal {v['nominal']:.2f}  p99 {v['p99']:.2f}  fail {v['fail_%']}%")
