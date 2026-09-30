"""
Minimal linear AC nodal solver returning N-port S-parameters.

Circuit description: list of elements (kind, node_a, node_b, value(s)).
Node 0 is ground. Ports are (node, Z0) pairs, all real reference impedances.

S-parameters use the power-wave definition with real Z0:
  Yt = Y + diag(1/Z0 at port nodes)
  S_ij = (2 / sqrt(Z0_i Z0_j)) * [Yt^-1]_(port_i, port_j) - delta_ij
"""
import numpy as np


def _elem_admittance(kind, val, w):
    """Admittance of a two-terminal element at angular frequency w."""
    jw = 1j * w
    if kind == "R":
        return 1.0 / val
    if kind == "L":                      # ideal inductor
        return 1.0 / (jw * val)
    if kind == "C":                      # ideal capacitor
        return jw * val
    if kind == "Lreal":                  # (Rs + jwL) || Cp ; Rs from constant Q plus Rdc
        L, Q, Cp, Rdc = val
        Rs = Rdc + (w * L / Q if Q else 0.0)
        return 1.0 / (Rs + jw * L) + jw * Cp
    if kind == "Creal":                  # C + ESL + ESR in series
        C, ESL, ESR = val
        return 1.0 / (ESR + jw * ESL + 1.0 / (jw * C))
    if kind == "Lcc":                    # Coilcraft lumped model (Doc 158):
        L, R1, R2, C, k = val             # (R2 + k*sqrt(f) + jwL) || (R1 + 1/(jwC))
        f = w / (2 * np.pi)
        return 1.0 / (R2 + k * np.sqrt(f) + jw * L) + 1.0 / (R1 + 1.0 / (jw * C))
    raise ValueError(kind)


def sparams(elements, ports, freqs, n_nodes):
    """Return S array of shape (len(freqs), P, P)."""
    P = len(ports)
    S = np.zeros((len(freqs), P, P), dtype=complex)
    pn = [p[0] for p in ports]
    z0 = np.array([p[1] for p in ports], dtype=float)
    for k, f in enumerate(freqs):
        w = 2 * np.pi * f
        Y = np.zeros((n_nodes, n_nodes), dtype=complex)   # includes ground row/col 0
        for kind, a, b, val in elements:
            if kind == "TL2":                       # ideal TEM line, 2-port referenced to ground
                Zc, el_deg, f0 = val
                th = np.deg2rad(el_deg) * f / f0
                y11 = -1j / np.tan(th) / Zc; y12 = 1j / np.sin(th) / Zc
                Y[a, a] += y11; Y[b, b] += y11; Y[a, b] += y12; Y[b, a] += y12
                continue
            if kind == "VCCS":                      # current gm*(V(p)-V(n)) injected into node a; b unused
                p, n, gm = val
                Y[a, p] -= gm; Y[a, n] += gm
                continue
            y = _elem_admittance(kind, val, w)
            Y[a, a] += y
            Y[b, b] += y
            Y[a, b] -= y
            Y[b, a] -= y
        for (n, z) in ports:
            Y[n, n] += 1.0 / z
        Yr = Y[1:, 1:]                                      # remove ground
        idx = [n - 1 for n in pn]
        rhs = np.zeros((n_nodes - 1, P), dtype=complex)
        for j, i in enumerate(idx):
            rhs[i, j] = 1.0
        Zp = np.linalg.solve(Yr, rhs)[idx, :]               # [Yt^-1] at port nodes
        S[k] = 2.0 * Zp / np.sqrt(np.outer(z0, z0)) - np.eye(P)
    return S


def opamp(out, inp, inn, A=1e6, rout=1.0):
    """Ideal-ish op amp: VCCS gm = A/rout into 'out' plus rout to ground -> Vout = A (V+ - V-).
    Returns a list of elements. Ground-referenced output; no bandwidth or distortion modelled."""
    return [("VCCS", out, 0, (inp, inn, A / rout)), ("R", out, 0, rout)]


def node_voltages(elements, n_nodes, f, inj):
    """Solve Y V = I at frequency f for current injections {node: amps} (into the node).
    Returns V[0..n_nodes-1] with V[0] = 0 (ground). Handles VCCS and TL2 like sparams()."""
    w = 2 * np.pi * f
    Y = np.zeros((n_nodes, n_nodes), dtype=complex)
    for kind, a, b, val in elements:
        if kind == "TL2":
            Zc, el_deg, f0 = val; th = np.deg2rad(el_deg) * f / f0
            y11 = -1j / np.tan(th) / Zc; y12 = 1j / np.sin(th) / Zc
            Y[a, a] += y11; Y[b, b] += y11; Y[a, b] += y12; Y[b, a] += y12; continue
        if kind == "VCCS":
            p, n, gm = val; Y[a, p] -= gm; Y[a, n] += gm; continue
        y = _elem_admittance(kind, val, w if w > 0 else 1e-9)
        Y[a, a] += y; Y[b, b] += y; Y[a, b] -= y; Y[b, a] -= y
    I = np.zeros(n_nodes, dtype=complex)
    for nd, cur in inj.items(): I[nd] += cur
    V = np.zeros(n_nodes, dtype=complex)
    V[1:] = np.linalg.solve(Y[1:, 1:], I[1:])
    return V


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-15))


def loss_worst(s21):
    """Worst-case (largest) insertion loss in dB over the given samples.
    Use this instead of hand-writing -db(x).max()/min(): the '-db(x).max()' form
    returns the BEST case and caused two bugs in this project."""
    return float(-db(s21).min())


def loss_best(s21):
    """Best-case (smallest) insertion loss in dB."""
    return float(-db(s21).max())


def rl_worst(s11):
    """Worst-case (smallest) return loss in dB."""
    return float(-db(s11).max())


if __name__ == "__main__":
    # TL2: a short high-impedance line must look like L = Zc*tau in series (low f)
    Zc, el, f0 = 1230.0, 49.2, 1040e6
    tau = el / 360 / f0
    for f in (1e6, 30e6):
        Sl = sparams([("TL2", 1, 2, (Zc, el, f0))], [(1, 50.0), (2, 50.0)], [f], 3)
        Si = sparams([("L", 1, 2, Zc * tau)], [(1, 50.0), (2, 50.0)], [f], 3)
        assert abs(Sl[0, 1, 0] - Si[0, 1, 0]) < 2e-3, (f, Sl[0, 1, 0], Si[0, 1, 0])
    # a quarter-wave 50-ohm line is matched and gives -90 degrees
    Sq = sparams([("TL2", 1, 2, (50.0, 90.0, 100e6))], [(1, 50.0), (2, 50.0)], [100e6], 3)
    assert abs(Sq[0, 0, 0]) < 1e-9 and abs(Sq[0, 1, 0] - (-1j)) < 1e-9, Sq
    # op amp model: inverting (-Rf/Rg), non-inverting (1+Rf/Rg), difference amplifier
    Rg, Rf = 100.0, 237.0
    # inverting: source 1 V via Norton (1/Rs A into node 1 with Rs to ground), node1 -Rg- node2(-) , Rf 2-3, out=3, + at ground
    el = [("R", 1, 0, 1e-3), ("R", 1, 2, Rg), ("R", 2, 3, Rf)] + opamp(3, 0, 2)
    V = node_voltages(el, 4, 1e6, {1: 1.0 / 1e-3})
    assert abs(V[3] / V[1] - (-Rf / Rg)) < 1e-4, V[3] / V[1]
    # non-inverting: input on +, Rg from - to ground, Rf -/out
    el = [("R", 1, 0, 1e-3), ("R", 2, 0, Rg), ("R", 2, 3, Rf)] + opamp(3, 1, 2)
    V = node_voltages(el, 4, 1e6, {1: 1.0 / 1e-3})
    assert abs(V[3] / V[1] - (1 + Rf / Rg)) < 1e-4, V[3] / V[1]
    # difference amp, all resistors R: Vout = V(a) - V(b)... here Va on + path, Vb on - path
    R = 237.0
    el = [("R", 1, 0, 1e-3), ("R", 4, 0, 1e-3), ("R", 4, 2, R), ("R", 2, 3, R),
          ("R", 1, 5, R), ("R", 5, 0, R)] + opamp(3, 5, 2)
    V = node_voltages(el, 6, 1e6, {1: 0.7 / 1e-3, 4: 0.2 / 1e-3})
    assert abs(V[3] - (V[1] - V[4])) < 1e-4, (V[3], V[1], V[4])
    x = np.array([1.0, 10 ** (-1 / 20), 10 ** (-3 / 20)])
    assert abs(loss_worst(x) - 3.0) < 1e-9 and abs(loss_best(x) - 0.0) < 1e-9
    g = np.array([0.1, 0.5])
    assert abs(rl_worst(g) - 6.0206) < 1e-3
    print("netsolve helper tests OK")
