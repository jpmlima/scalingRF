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
    x = np.array([1.0, 10 ** (-1 / 20), 10 ** (-3 / 20)])
    assert abs(loss_worst(x) - 3.0) < 1e-9 and abs(loss_best(x) - 0.0) < 1e-9
    g = np.array([0.1, 0.5])
    assert abs(rl_worst(g) - 6.0206) < 1e-3
    print("netsolve helper tests OK")
