"""Re-check HF preselector desense with REAL pre-LNA switch losses (explicit pass lists).
Audit found the old noise model counted one 0.3 dB switch before the LNA; the preselector
band-select switches (in and out) were never included."""
import os, json
import numpy as np
import dip_presel as D, mc_chain as MC
import preselector as P
from netsolve import sparams, db
from noise_budget import desense, DESENSE_MAX

from noise_budget import LEGACY_PRE_LNA
# explicit pre-LNA pass lists (dB per pass)
SCEN = {"S0 as modelled (1 x 0.3 dB)": LEGACY_PRE_LNA,
        "S1 current topology, PE42582-class (3 x 0.7 dB)": {"LNA/bypass SPDT": 0.7, "presel in SP3T": 0.7, "presel out SP3T": 0.7},
        "S2 merged SP4T in + SP3T out (2 x 0.7 dB)": {"SP4T in": 0.7, "SP3T out": 0.7},
        "S3 signal relays (2 x 0.1 dB, ASSUMED)": {"relay SP4T in": 0.1, "relay SP3T out": 0.1},
        "S4 Omron G6KU-2F-RF, datasheet MAX @1 GHz (2 x 0.2 dB)": {"G6KU pole A (filter in)": 0.2, "G6KU pole B (filter out)": 0.2}}
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
    for name, passes in SCEN.items():
        ds = np.array([desense(fb / 1e6, p, pre=passes).max() for p in presel])
        out[band][name] = {"nominal": round(float(ds[0]), 2), "p99": round(float(np.percentile(ds[1:], 99)), 2),
                           "fail_%": round(100 * float(np.mean(ds[1:] > DESENSE_MAX[band])), 1)}
json.dump(out, open(os.path.join(D.HERE, "switch_recheck.json"), "w"), indent=1)
for b, d in out.items():
    print(f"{b} (limit {DESENSE_MAX[b]} dB)")
    for k, v in d.items(): print(f"   {k:48s} nominal {v['nominal']:.2f}  p99 {v['p99']:.2f}  fail {v['fail_%']}%")
