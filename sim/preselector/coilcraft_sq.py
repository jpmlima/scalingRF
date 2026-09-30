"""Coilcraft 1515SQ / 2222SQ / 2929SQ air-core inductors, transmission-line model
(Document 836-2, rev 09/08/17). Model: P1 -R2- [ideal TL: Z0, EL deg at F0] - P2,
with (R1 + C) across P1-P2. Valid 10 MHz .. 'upper' (MHz).
Hand check: 2222SQ-161 -> L = Z0*tau = 161.7 nH (datasheet 160), Q@50MHz = 142 (datasheet 140)."""
_T = """1515SQ-47N 10 2000 26.74 0.253 0.1886 308 48.6 940
1515SQ-68N 10 2250 21.52 0.463 0.1066 460 51.3 1000
1515SQ-82N 10 2000 10.76 0.607 0.1186 448 60.9 950
2222SQ-90N 10 1400 93.6 0.203 0.1796 604 56.4 1050
2222SQ-111 10 1200 234.6 0.248 0.1352 920 44.4 1030
2222SQ-131 10 1200 438.6 0.293 0.0842 1030 44.4 970
2222SQ-161 10 900 828.8 0.357 0.0558 1230 49.2 1040
2222SQ-181 10 800 1179 0.362 0.1506 1370 49.2 1040
2222SQ-221 10 850 4375 0.488 0.0508 1190 65.3 980
2222SQ-271 10 800 4855 0.600 0.0438 1430 65.3 960
2222SQ-301 10 500 5107 0.608 0.0226 1650 74.0 1140
2929SQ-331 10 650 10009 0.561 0.0365 2035 81.0 1390
2929SQ-361 10 600 9697 0.607 0.0355 2220 81.0 1390
2929SQ-391 10 550 9594 0.659 0.0360 2405 81.0 1390
2929SQ-431 10 500 3647 0.741 0.0365 2650 81.0 1390
2929SQ-501 10 400 2847 1.031 0.0385 3090 81.0 1390"""
SQ = {}
for line in _T.splitlines():
    n, lo, up, R1, R2, C, Z0, EL, F0 = line.split()
    SQ[n] = dict(R1=float(R1), R2=float(R2), C=float(C) * 1e-12, Z0=float(Z0), EL=float(EL),
                 F0=float(F0) * 1e6, lo=float(lo) * 1e6, up=float(up) * 1e6)
    SQ[n]["L"] = SQ[n]["Z0"] * SQ[n]["EL"] / 360 / SQ[n]["F0"]


def z_model(name, f):
    """Closed form of the model with P2 grounded: (R2 + j Z0 tan(theta)) || (R1 + 1/(j w C))."""
    import numpy as np
    p = SQ[name]; w = 2 * np.pi * f
    th = np.deg2rad(p["EL"]) * f / p["F0"]
    z1 = p["R2"] + 1j * p["Z0"] * np.tan(th)
    z2 = p["R1"] + 1 / (1j * w * p["C"])
    return z1 * z2 / (z1 + z2)


def q_at(name, f):
    """Q from a 1-port simulation (P2 grounded) through the solver — exact, no series-element assumption."""
    import numpy as np
    from netsolve import sparams
    p = SQ[name]
    el = [("R", 1, 2, p["R2"]), ("TL2", 2, 0, (p["Z0"], p["EL"], p["F0"])), ("R", 1, 3, p["R1"]), ("C", 3, 0, p["C"])]
    s11 = sparams(el, [(1, 50.0)], [f], 4)[0, 0, 0]
    Z = 50.0 * (1 + s11) / (1 - s11)
    zc = z_model(name, f)
    assert abs(Z - zc) / abs(zc) < 1e-6, (Z, zc)          # solver == closed form
    return Z.imag / Z.real
