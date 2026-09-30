"""Allowed preselector loss vs frequency, from the validated HF RX noise lineup (sim/hf_rx)
and the external floor (ITU-R P.372 galactic + quiet rural)."""
import sys, os, io, contextlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hf_rx"))
with contextlib.redirect_stdout(io.StringIO()):
    import lineup as L, modes as M

DS_F = np.array([0.1, 1, 10, 50, 100]); DS_NF = np.array([6.67, 3.93, 3.65, 2.92, 3.10]); G = 15.9
lin = lambda x: 10 ** (np.asarray(x, float) / 10)
DESENSE_MAX = {"B1": 1.0, "B2": 1.0, "B3": 1.5}


def nf_sys(f_mhz, presel_db):
    dip = np.interp(f_mhz, [0.001, 10, 30, 49], [0.14, 0.27, 0.5, 1.0])
    aaf = np.interp(f_mhz, [0.001, 30, 49], [0.3, 0.5, 0.9])
    fpost = lin(M.SW + M.SW + aaf + M.nf_b); nfl = np.interp(f_mhz, DS_F, DS_NF)
    return 10 * np.log10(lin(dip + M.SW + presel_db) * (lin(nfl) + (fpost - 1) / lin(G)))


def desense(f_mhz, presel_db):
    ext = lin(L.fa("galactic", f_mhz)) + lin(L.fa("quiet rural", f_mhz))
    return 10 * np.log10((ext + lin(nf_sys(f_mhz, presel_db)) - 1) / ext)


def budget_curve(f_hz, dmax):
    """Max preselector loss (dB) at each frequency for desense <= dmax."""
    out = []
    for f in np.atleast_1d(f_hz) / 1e6:
        lo, hi = 0.0, 20.0
        if desense(f, 0.0) > dmax: out.append(0.0); continue
        for _ in range(40):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if desense(f, mid) <= dmax else (lo, mid)
        out.append(lo)
    return np.array(out)
