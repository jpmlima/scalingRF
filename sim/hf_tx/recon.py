"""Reconstruction filter designed INSIDE the TX chain.
Ports: 1 = filter input (LMH6702 back-terminated, 50 ohm), 2 = TX antenna port (diplexer common),
3 = diplexer HP port (AD9361 TX path, 50 ohm). Filter: elliptic 5th order, minimum-inductor form
  C1 shunt | L2 || Cz2 | C3 shunt | L4 || Cz4 | C5 shunt  -> diplexer LP port.
Metrics on the real chain: image at the port <= -60 dBc (design margin 3 dB) for tones 20-49 MHz,
filter share of passband loss <= 1 dB (DC-49 MHz), input RL >= 14 dB, HP arm unaffected."""
import sys, os, json, itertools
import numpy as np
from scipy.optimize import least_squares
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("diplexer", "preselector"):
    sys.path.insert(0, os.path.join(HERE, "..", d))
import real_parts as DIP
import preselector as P                      # Net, PAR, snapE24, PARTS, L_AVAIL
from netsolve import sparams, db, loss_worst, rl_worst
import tx_lineup as TX

FS = TX.FS
DIP_L, DIP_C = TX.DIP_L, TX.DIP_C
NAMES = ["C1", "L2", "Cz2", "C3", "L4", "Cz4", "C5"]
IS_L = np.array([n.startswith("L") for n in NAMES])
TONES = np.linspace(20e6, 49e6, 30)
F_PASS = np.linspace(0.1e6, 49e6, 40)


def build_filter(v, lmodel, net, p_in, p_out):
    def gnd():
        g = net.node(); net.add("L", g, 0, P.PAR["via_L"], pads=False); return g
    def cap(a, b, c): net.add("Creal", a, b, (c, P.PAR["C_ESL"], P.PAR["C_ESR"]))
    li = iter(range(2))
    def ind(a, b, L):
        i = next(li)
        if lmodel[0] == "Q": net.add("Lreal", a, b, (L, lmodel[1], 0.0, 0.0))
        else:
            Lp, R1, R2, C, k, _ = P.PARTS[lmodel[1][i]]; net.add("Lcc", a, b, (Lp, R1, R2, C, k))
    C1, L2, Cz2, C3, L4, Cz4, C5 = v
    x = p_in
    cap(x, gnd(), C1); y = net.node(); ind(x, y, L2); cap(x, y, Cz2); x = y
    cap(x, gnd(), C3); y = net.node(); ind(x, y, L4); cap(x, y, Cz4); x = y
    cap(x, gnd(), C5)
    net.add("L", x, p_out, 0.45e-9, pads=False)          # short trace to the switch / diplexer LP port


def chain(v, lmodel):
    el_d, ports_d, nn_d = DIP.build_real(DIP_L, DIP_C)
    (com, _), (lp, _), (hp, _) = ports_d
    net = P.Net(); net.n = nn_d                          # continue numbering after the diplexer
    p_in = net.node()
    build_filter(v, lmodel, net, p_in, lp)
    for nd, c in net.pads.items(): net.el.append(("C", nd, 0, c * P.PAR["pad_C"]))
    return list(el_d) + net.el, [(p_in, 50.0), (com, 50.0), (hp, 50.0)], net.n


def sim(v, lmodel, F):
    el, ports, nn = chain(v, lmodel)
    return sparams(el, ports, F, nn)


F_ALL = np.unique(np.concatenate([F_PASS, TONES, FS - TONES]))
DIP_ALONE = DIP.sim(DIP_L, DIP_C, F_ALL)[:, 1, 0]


def metrics(S, F=F_ALL, dip=DIP_ALONE):
    A = -db(S[:, 1, 0]); Ai = lambda f: np.interp(f, F, A)
    img = TX.image_dbc(TONES) - (Ai(FS - TONES) - Ai(TONES))           # image level at the port, dBc
    pas = (F <= 49e6)
    filt_loss = A[pas] - (-db(dip[pas]))                                # filter share of passband loss
    return {"image_worst_dBc": float(img.max()), "image_worst_tone_MHz": float(TONES[np.argmax(img)] / 1e6),
            "filter_loss_worst_dB": float(filt_loss.max()), "filter_loss_min_dB": float(filt_loss.min()),
            "input_RL_worst_dB": rl_worst(S[pas, 0, 0])}, img, filt_loss


def resid(x, lmodel, fixed=None):
    v = np.exp(x)
    if fixed is not None:
        full = np.array(fixed, float); full[~IS_L] = v; v = full
    S = sim(v, lmodel, F_ALL)
    m, img, fl = metrics(S)
    r = list(np.maximum(0, img - (-63.0)))                               # -60 dBc with 3 dB margin
    r += list(2 * np.maximum(0, fl - 0.8)) + list(0.3 * fl)
    pas = (F_ALL <= 49e6)
    r += list(0.3 * np.maximum(0, 15 - (-db(S[pas, 0, 0]))))
    return np.array(r)


def start():
    # 5th-order 0.1 dB Chebyshev prototype, fc 52 MHz, shunt-C first; zeros at ~105 and ~130 MHz
    g = [1.1468, 1.3712, 1.9750, 1.3712, 1.1468]; wc = 2 * np.pi * 52e6; Z0 = 50.0
    C1, L2, C3, L4, C5 = g[0] / (Z0 * wc), g[1] * Z0 / wc, g[2] / (Z0 * wc), g[3] * Z0 / wc, g[4] / (Z0 * wc)
    Cz2 = 1 / ((2 * np.pi * 105e6) ** 2 * L2); Cz4 = 1 / ((2 * np.pi * 130e6) ** 2 * L4)
    return np.array([C1, L2, Cz2, C3, L4, Cz4, C5])


if __name__ == "__main__":
    lo = np.log(np.where(IS_L, 10e-9, 0.5e-12)); hi = np.log(np.where(IS_L, 820e-9, 1e-9))
    x0 = np.clip(np.log(start()), lo + 1e-6, hi - 1e-6)
    solA = least_squares(resid, x0, args=(("Q", 45.0),), bounds=(lo, hi), max_nfev=60)
    vA = np.exp(solA.x)
    cands = [sorted(P.L_AVAIL, key=lambda n: abs(np.log(P.PARTS[n][0] / L)))[:3] for L in vA[IS_L]]
    best = None
    for combo in itertools.product(*cands):
        fixed = vA.copy(); fixed[IS_L] = [P.PARTS[n][0] for n in combo]
        sol = least_squares(resid, np.log(vA[~IS_L]), args=(("parts", combo), fixed),
                            bounds=(lo[~IS_L], hi[~IS_L]), max_nfev=25)
        v = fixed.copy(); v[~IS_L] = [P.snapE24(c) for c in np.exp(sol.x)]
        m, _, _ = metrics(sim(v, ("parts", combo), F_ALL))
        score = -max(0, m["image_worst_dBc"] + 60) * 3 - max(0, m["filter_loss_worst_dB"] - 1.0) * 5 \
                - max(0, 14 - m["input_RL_worst_dB"]) - 0.5 * m["filter_loss_worst_dB"] - 0.05 * (m["image_worst_dBc"] + 60)
        if best is None or score > best[0]: best = (score, combo, v, m)
    _, combo, v, m = best
    out = {"inductors": list(combo), "caps_pF": {n: round(float(c) * 1e12, 1) for n, c in zip(NAMES, v) if not n.startswith("L")},
           "values": [float(x) for x in v], **{k: round(x, 2) for k, x in m.items()}}
    json.dump(out, open(os.path.join(HERE, "recon_design.json"), "w"), indent=1)
    print(json.dumps({k: out[k] for k in out if k != "values"}, indent=1))
