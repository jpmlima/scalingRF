"""Frequency-by-frequency desense of a preselector design vs the external floor
(ITU-R P.372 galactic + quiet rural), using the validated HF RX lineup (sim/hf_rx)."""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
import preselector_ell as E
from netsolve import db
from noise_budget import desense


def report(band, v, lmodel):
    fl, fh = E.P.BANDS[band]
    f = np.linspace(fl, fh, 41)
    S = E.sim(v, lmodel, f)
    il = -db(S[:, 1, 0])
    d = desense(f / 1e6, il); d0 = desense(f / 1e6, 0 * il)
    k = np.argmax(d)
    return {"IL_dB_at": {f"{x/1e6:.1f}": round(float(y), 2) for x, y in zip(f[::8], il[::8])},
            "desense_worst_dB": round(float(d[k]), 2), "at_MHz": round(float(f[k] / 1e6), 1),
            "desense_without_preselector_same_f_dB": round(float(d0[k]), 2),
            "desense_added_by_preselector_worst_dB": round(float((d - d0).max()), 2)}


if __name__ == "__main__":
    b = sys.argv[1]
    j = json.load(open(os.path.join(HERE, f"ell_{b}.json")))
    print(b, json.dumps(report(b, np.array(j["values"]), ("parts", j["inductors"]))))
