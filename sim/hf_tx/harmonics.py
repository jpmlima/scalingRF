"""Harmonic filtering vs tone frequency: how clean must DAC + amplifier be (HDn at their output)
so every harmonic is <= -60 dBc at the TX port. Reconstruction filter = placeholder ideal
5th-order Chebyshev 0.1 dB, fc 50 MHz (the minimum order found by hand for 23 dB @ 101 MHz)."""
import os, json
import numpy as np
import lineup as L
from netsolve import db

EPS = np.sqrt(10 ** (0.1 / 10) - 1)


def cheb5_db(f, fc=50e6):
    w = f / fc
    t = np.where(w <= 1, np.cos(5 * np.arccos(np.minimum(w, 1))), np.cosh(5 * np.arccosh(np.maximum(w, 1))))
    return 10 * np.log10(1 + (EPS * t) ** 2)


if __name__ == "__main__":
    # hand check used to choose the order: 5th-order 0.1 dB Chebyshev at 2.06x fc
    assert abs(cheb5_db(101e6, 49e6) - 36.5) < 0.3, cheb5_db(101e6, 49e6)
    tones = np.array([5, 10, 15, 20, 24, 25, 26, 28, 30, 33, 36, 40, 45, 49]) * 1e6
    rows = []
    for n in (2, 3):
        fh = n * tones
        F = np.unique(np.concatenate([tones, fh]))
        S = L.DIP.sim(L.DIP_L, L.DIP_C, F); dip = dict(zip(F, -db(S[:, 1, 0])))
        for f, h in zip(tones, fh):
            filt = (cheb5_db(h) + dip[h]) - (cheb5_db(f) + dip[f])
            req = L.SPUR_TARGET_DBC + filt            # port level = HD - filt <= target  ->  HD <= target + filt
            rows.append({"n": n, "tone_MHz": f / 1e6, "harm_MHz": h / 1e6, "filtering_dB": round(float(filt), 1),
                         "HD_needed_at_amp_dBc": round(float(req), 1)})
    # sanity: more filtering must never make the requirement stricter
    for r in rows:
        assert abs(r["HD_needed_at_amp_dBc"] - (L.SPUR_TARGET_DBC + r["filtering_dB"])) < 0.11
    fl = sorted(rows, key=lambda r: r["filtering_dB"])
    assert all(a["HD_needed_at_amp_dBc"] <= b["HD_needed_at_amp_dBc"] + 1e-9 for a, b in zip(fl, fl[1:]))
    json.dump(rows, open(os.path.join(L.HERE, "harmonics_results.json"), "w"), indent=1)
    for r in rows:
        print(r)
