"""Allowed preselector loss vs frequency, from the validated HF RX noise lineup (sim/hf_rx)
and the external floor (ITU-R P.372 galactic + quiet rural).

Every switch/relay pass in the HF LNA path is listed EXPLICITLY below (lesson from D20: the
preselector's band-select switches were once missing from this model). Change the lists, not
the formulas. LEGACY_PRE_LNA reproduces the pre-D20 model exactly (regression test in __main__)."""
import sys, os, io, contextlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "hf_rx"))
with contextlib.redirect_stdout(io.StringIO()):
    import lineup as L, modes as M

DS_F = np.array([0.1, 1, 10, 50, 100]); DS_NF = np.array([6.67, 3.93, 3.65, 2.92, 3.10]); G = 15.9
lin = lambda x: 10 ** (np.asarray(x, float) / 10)
DESENSE_MAX = {"B1": 1.0, "B2": 1.0, "B3": 1.5}

# ---- switching in the HF LNA path, one entry per pass (dB) ----
# before the LNA (D20: relays, SP4T in = bypass + 3 bands, SP3T out to the LNA) — ASSUMED until parts chosen
PRE_LNA = {"relay SP4T in (bypass/B1/B2/B3)": 0.1, "relay SP3T out (to LNA)": 0.1}
# after the LNA (noise-insensitive; semiconductor switches acceptable)
POST_LNA = {"LNA/bypass merge switch": 0.3, "attenuator path switch": 0.3}
LEGACY_PRE_LNA = {"single 0.3 dB switch (pre-D20 model, incomplete)": 0.3}


def pre_lna_loss(pre=None):
    return sum((PRE_LNA if pre is None else pre).values())


def nf_sys(f_mhz, presel_db, pre=None):
    """presel_db = filter loss only (switching is in PRE_LNA / POST_LNA)."""
    dip = np.interp(f_mhz, [0.001, 10, 30, 49], [0.14, 0.27, 0.5, 1.0])
    aaf = np.interp(f_mhz, [0.001, 30, 49], [0.3, 0.5, 0.9])
    fpost = lin(sum(POST_LNA.values()) + aaf + M.nf_b); nfl = np.interp(f_mhz, DS_F, DS_NF)
    return 10 * np.log10(lin(dip + pre_lna_loss(pre) + presel_db) * (lin(nfl) + (fpost - 1) / lin(G)))


def desense(f_mhz, presel_db, pre=None):
    ext = lin(L.fa("galactic", f_mhz)) + lin(L.fa("quiet rural", f_mhz))
    return 10 * np.log10((ext + lin(nf_sys(f_mhz, presel_db, pre)) - 1) / ext)


def budget_curve(f_hz, dmax, pre=None):
    """Max preselector loss (dB) at each frequency for desense <= dmax."""
    out = []
    for f in np.atleast_1d(f_hz) / 1e6:
        lo, hi = 0.0, 20.0
        if desense(f, 0.0, pre) > dmax: out.append(0.0); continue
        for _ in range(40):
            mid = (lo + hi) / 2
            (lo, hi) = (mid, hi) if desense(f, mid, pre) <= dmax else (lo, mid)
        out.append(lo)
    return np.array(out)


if __name__ == "__main__":
    # regression: the legacy pass list must reproduce the pre-D20 numbers exactly
    assert POST_LNA and abs(sum(POST_LNA.values()) - 2 * M.SW) < 1e-12
    b49 = budget_curve(np.array([49e6]), 1.5, LEGACY_PRE_LNA)[0]
    b38 = budget_curve(np.array([38e6]), 1.0, LEGACY_PRE_LNA)[0]
    assert abs(b49 - 2.14) < 0.01 and abs(b38 - 3.04) < 0.01, (b49, b38)
    print("regression OK (legacy model): budget @49 MHz %.2f dB, @38 MHz %.2f dB" % (b49, b38))
    print("current model: pre-LNA passes", PRE_LNA, "-> total %.2f dB" % pre_lna_loss())
    print("budget @49 MHz (<=1.5 dB desense) now %.2f dB" % budget_curve(np.array([49e6]), 1.5)[0])
