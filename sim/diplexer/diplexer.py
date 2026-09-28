"""
scalingRF — port diplexer: HF arm (DC..~55 MHz) / VHF-SHF arm (~65 MHz..6 GHz).

Ports: 1 = common (antenna side), 2 = LP / HF, 3 = HP / AD9361 side. All 50 ohm.

Stages:
  A. Ideal design: 7th-order LP (series-L first) and HP (series-C first) in
     parallel at the common node, start from Butterworth g-values, then
     numerically optimise the 14 values against the spec.
  B. Snap to purchasable values (L: E12 series, C: E24 series).
  C. Same values with real-component parasitics + layout parasitics.
  D. Variant: first LP element as a broadband (conical) inductor.
  E. Monte Carlo over tolerances.

Parasitic models are generic placeholders and MUST be replaced with the
manufacturer S-parameter files of the actual parts before layout. See README.
"""
import json
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from netsolve import sparams, db

Z0 = 50.0
N_LP = 5
N_HP = 5
FC = 60e6

# ---------------- spec ----------------
SPEC = {
    "lp_pass_max_hz": 50e6, "lp_il_max_db": 1.0,
    "hp_pass_min_hz": 70e6, "hp_pass_max_hz": 6e9, "hp_il_max_db": 1.0,
    "rl_min_db": 10.0,            # common-port return loss in both passbands
    "hp_rej_hz": 30e6, "hp_rej_min_db": 30.0,   # keep strong HF out of the AD9361 LNA
    "lp_rej_hz": 120e6, "lp_rej_min_db": 30.0,  # keep VHF/FM out of the HF chain
}

# ------------- parasitic models (generic, to be replaced) -------------
PAR = {
    "L_Q": 60.0,          # REQUIREMENT: Q >= 60 at 50-70 MHz (constant-Q approximation)
    "L_Cp": 0.12e-12,     # shunt parasitic C -> sets SRF
    "L_Rdc": 0.1,
    "C_ESL": 0.35e-9,     # 0402 C0G incl. part of mounting
    "C_ESR": 0.15,
    "pad_C": 0.05e-12,    # per 0402 pad over ground at ~0.2 mm
    "tl_len": 1.5e-3,     # trace between HP elements / at junction
    "tl_eeff": 3.3,
    "tl_Z": 50.0,
    "conical_Cp": 0.02e-12,   # broadband conical inductor, effective (optimistic)
    "conical_Q": 20.0,
    "via_L": 0.4e-9,      # via to ground plane, per shunt element (single via)
}

E12 = np.array([1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2])
E24 = np.array([1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
                3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1])


def snap(v, series):
    e = np.floor(np.log10(v))
    m = v / 10 ** e
    cands = np.concatenate([series, [10.0]])
    best = cands[np.argmin(np.abs(np.log(cands / m)))]
    return best * 10 ** e


def _g(n):
    return [2 * np.sin((2 * k - 1) * np.pi / (2 * n)) for k in range(1, n + 1)]


def butterworth_start():
    wc = 2 * np.pi * FC
    lp = [(g * Z0 / wc) if k % 2 else (g / (Z0 * wc)) for k, g in enumerate(_g(N_LP), start=1)]
    hp = [(1 / (g * Z0 * wc)) if k % 2 else (Z0 / (g * wc)) for k, g in enumerate(_g(N_HP), start=1)]
    return np.array(lp), np.array(hp)


# Buildable ranges: 0603 wirewound L, 0402 C0G C
L_MIN, L_MAX = 10e-9, 680e-9
C_MIN, C_MAX = 1e-12, 330e-12


def bounds():
    lo, hi = [], []
    for k in range(1, N_LP + 1):
        lo.append(L_MIN if k % 2 else C_MIN); hi.append(L_MAX if k % 2 else C_MAX)
    for k in range(1, N_HP + 1):
        lo.append(C_MIN if k % 2 else L_MIN); hi.append(C_MAX if k % 2 else L_MAX)
    return np.log(lo), np.log(hi)


# ---------------- netlist builder ----------------
class Net:
    def __init__(self):
        self.el = []
        self.n = 1          # next free node (0 = ground)
        self.padcount = {}

    def node(self):
        self.n += 1
        return self.n - 1

    def add(self, kind, a, b, val, pads=True):
        self.el.append((kind, a, b, val))
        if pads:
            for nd in (a, b):
                if nd:
                    self.padcount[nd] = self.padcount.get(nd, 0) + 1

    def finish(self, parasitic):
        if parasitic:
            for nd, cnt in self.padcount.items():
                self.el.append(("C", nd, 0, cnt * PAR["pad_C"]))
        return self.el, self.n


def add_L(net, a, b, L, parasitic, conical=False):
    if not parasitic:
        net.add("L", a, b, L)
    elif conical:
        net.add("Lreal", a, b, (L, PAR["conical_Q"], PAR["conical_Cp"], PAR["L_Rdc"]))
    else:
        net.add("Lreal", a, b, (L, PAR["L_Q"], PAR["L_Cp"], PAR["L_Rdc"]))


def add_C(net, a, b, C, parasitic):
    if not parasitic:
        net.add("C", a, b, C)
    else:
        net.add("Creal", a, b, (C, PAR["C_ESL"], PAR["C_ESR"]))


def shunt_node(net, parasitic):
    """Ground-side node for a shunt element: real ground, or ground through a via."""
    if not parasitic:
        return 0
    g = net.node()
    net.add("L", g, 0, PAR["via_L"], pads=False)
    return g


def add_tl(net, a, parasitic):
    """Short 50-ohm trace as a lumped pi section. Returns the far node."""
    if not parasitic:
        return a
    b = net.node()
    tau = PAR["tl_len"] * np.sqrt(PAR["tl_eeff"]) / 3e8
    Lt, Ct = PAR["tl_Z"] * tau, tau / PAR["tl_Z"]
    net.add("C", a, 0, Ct / 2, pads=False)
    net.add("L", a, b, Lt, pads=False)
    net.add("C", b, 0, Ct / 2, pads=False)
    return b


def build(lp, hp, parasitic=False, conical_first=False):
    net = Net()
    com = net.node()                       # node 1
    p2 = None
    # ---- LP arm: L1 series, C2 shunt, L3 series, ... L7 series -> port 2
    x = add_tl(net, com, parasitic)
    for k, v in enumerate(lp, start=1):
        if k % 2:
            y = net.node()
            add_L(net, x, y, v, parasitic, conical=(conical_first and k == 1))
            x = y
        else:
            add_C(net, x, shunt_node(net, parasitic), v, parasitic)
    p2 = x
    # ---- HP arm: C1 series, L2 shunt, C3 series, ... C7 series -> port 3
    x = add_tl(net, com, parasitic)
    for k, v in enumerate(hp, start=1):
        if k % 2:
            y = net.node()
            add_C(net, x, y, v, parasitic)
            x = add_tl(net, y, parasitic) if k < len(hp) else y
        else:
            add_L(net, x, shunt_node(net, parasitic), v, parasitic)
    p3 = x
    el, nn = net.finish(parasitic)
    return el, [(com, Z0), (p2, Z0), (p3, Z0)], nn


def simulate(lp, hp, freqs, **kw):
    el, ports, nn = build(lp, hp, **kw)
    return sparams(el, ports, freqs, nn)


# ---------------- ideal optimisation ----------------
F_LP = np.logspace(3, np.log10(SPEC["lp_pass_max_hz"]), 40)
F_HP = np.logspace(np.log10(SPEC["hp_pass_min_hz"]), np.log10(SPEC["hp_pass_max_hz"]), 60)
F_OPT = np.concatenate([F_LP, F_HP, [SPEC["hp_rej_hz"], SPEC["lp_rej_hz"]]])


def residuals(logv):
    v = np.exp(logv)
    S = simulate(v[:N_LP], v[N_LP:], F_OPT)
    nlp, nhp = len(F_LP), len(F_HP)
    r = []
    r += list(np.maximum(0, -db(S[:nlp, 1, 0]) - 0.3))              # LP IL
    r += list(np.maximum(0, -db(S[nlp:nlp + nhp, 2, 0]) - 0.3))     # HP IL
    r += list(0.3 * np.maximum(0, db(S[:nlp + nhp, 0, 0]) + 18))    # RL >= 18 dB target
    r.append(0.2 * max(0, db(S[-2, 2, 0]) + SPEC["hp_rej_min_db"] + 5))
    r.append(0.2 * max(0, db(S[-1, 1, 0]) + SPEC["lp_rej_min_db"] + 5))
    return np.array(r)


def check(S, f):
    """Evaluate the spec on a dense sweep. Returns dict of worst cases."""
    lp_band = f <= SPEC["lp_pass_max_hz"]
    hp_band = (f >= SPEC["hp_pass_min_hz"]) & (f <= SPEC["hp_pass_max_hz"])
    out = {
        "lp_il_worst_db": float(-db(S[lp_band, 1, 0]).min()),
        "hp_il_worst_db": float(-db(S[hp_band, 2, 0]).min()),
        "rl_lp_worst_db": float(-db(S[lp_band, 0, 0]).max()),
        "rl_hp_worst_db": float(-db(S[hp_band, 0, 0]).max()),
        "hp_rej_at_30MHz_db": float(-db(S[np.argmin(abs(f - SPEC["hp_rej_hz"])), 2, 0])),
        "lp_rej_at_120MHz_db": float(-db(S[np.argmin(abs(f - SPEC["lp_rej_hz"])), 1, 0])),
    }
    out["pass"] = bool(out["lp_il_worst_db"] <= SPEC["lp_il_max_db"]
                       and out["hp_il_worst_db"] <= SPEC["hp_il_max_db"]
                       and min(out["rl_lp_worst_db"], out["rl_hp_worst_db"]) >= SPEC["rl_min_db"]
                       and out["hp_rej_at_30MHz_db"] >= SPEC["hp_rej_min_db"]
                       and out["lp_rej_at_120MHz_db"] >= SPEC["lp_rej_min_db"])
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        N_LP = N_HP = int(sys.argv[1])
    SUF = f"_n{N_LP}"
    F = np.unique(np.concatenate([np.logspace(3, np.log10(6e9), 1500),
                                  [SPEC["hp_rej_hz"], SPEC["lp_rej_hz"]]]))
    results = {}

    lp0, hp0 = butterworth_start()
    S_bw = simulate(lp0, hp0, F)
    results["A0_butterworth_start"] = check(S_bw, F)

    lo, hi = bounds()
    x0 = np.clip(np.log(np.concatenate([lp0, hp0])), lo + 1e-6, hi - 1e-6)
    sol = least_squares(residuals, x0, bounds=(lo, hi), max_nfev=4000)
    v = np.exp(sol.x)
    lp_i, hp_i = v[:N_LP], v[N_LP:]
    S_id = simulate(lp_i, hp_i, F)
    results["A_ideal_optimised"] = check(S_id, F)

    lp_s = np.array([snap(x, E12) if k % 2 == 0 else snap(x, E24) for k, x in enumerate(lp_i)])
    hp_s = np.array([snap(x, E24) if k % 2 == 0 else snap(x, E12) for k, x in enumerate(hp_i)])
    S_sn = simulate(lp_s, hp_s, F)
    results["B_snapped_ideal"] = check(S_sn, F)

    S_re = simulate(lp_s, hp_s, F, parasitic=True)
    results["C_snapped_parasitic_wirewound"] = check(S_re, F)

    S_co = simulate(lp_s, hp_s, F, parasitic=True, conical_first=True)
    results["D_snapped_parasitic_conical_L1"] = check(S_co, F)

    # ---------------- Monte Carlo on variant C (all wirewound) ----------------
    rng = np.random.default_rng(1)
    runs, fails, worst = 500, 0, []
    FM = np.unique(np.concatenate([np.logspace(3, np.log10(6e9), 400),
                                   [SPEC["hp_rej_hz"], SPEC["lp_rej_hz"]]]))
    base = dict(PAR)
    for _ in range(runs):
        def tol(x, is_L):
            if is_L:
                return x * (1 + rng.uniform(-0.02, 0.02))
            return max(x * (1 + rng.uniform(-0.02, 0.02)), x + rng.uniform(-0.1e-12, 0.1e-12))
        lpm = np.array([tol(x, k % 2 == 0) for k, x in enumerate(lp_s)])
        hpm = np.array([tol(x, k % 2 == 1) for k, x in enumerate(hp_s)])
        for key in ("L_Cp", "C_ESL", "pad_C", "conical_Cp"):
            PAR[key] = base[key] * (1 + rng.uniform(-0.2, 0.2))
        c = check(simulate(lpm, hpm, FM, parasitic=True, conical_first=False), FM)
        worst.append(c)
        fails += (not c["pass"])
    PAR.update(base)
    results["E_monte_carlo_C_wirewound"] = {
        "runs": runs, "fail_rate": fails / runs,
        "lp_il_p99_db": float(np.percentile([w["lp_il_worst_db"] for w in worst], 99)),
        "hp_il_p99_db": float(np.percentile([w["hp_il_worst_db"] for w in worst], 99)),
        "rl_min_p1_db": float(np.percentile([min(w["rl_lp_worst_db"], w["rl_hp_worst_db"]) for w in worst], 1)),
    }

    results["values"] = {
        "LP_ideal": [float(x) for x in lp_i], "HP_ideal": [float(x) for x in hp_i],
        "LP_snapped": [float(x) for x in lp_s], "HP_snapped": [float(x) for x in hp_s],
    }
    results["spec"] = SPEC
    results["parasitics"] = PAR
    with open(f"results{SUF}.json", "w") as fh:
        json.dump(results, fh, indent=2)

    # ---------------- plots ----------------
    fig, ax = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    for S, lab, ls in [(S_sn, "ideal (snapped)", "--"), (S_re, "parasitic, wirewound L1", "-"),
                       (S_co, "parasitic, conical L1", "-")]:
        ax[0].semilogx(F, db(S[:, 1, 0]), ls, label=f"LP S21 {lab}")
        ax[0].semilogx(F, db(S[:, 2, 0]), ls, label=f"HP S31 {lab}")
        ax[1].semilogx(F, db(S[:, 0, 0]), ls, label=f"S11 {lab}")
    ax[0].set_ylim(-60, 2); ax[0].set_ylabel("dB"); ax[0].grid(True, which="both", alpha=.3)
    ax[0].axvline(50e6, c="k", lw=.5); ax[0].axvline(70e6, c="k", lw=.5)
    ax[0].legend(fontsize=7); ax[0].set_title("scalingRF diplexer — transmission")
    ax[1].set_ylim(-40, 0); ax[1].set_ylabel("S11 dB"); ax[1].set_xlabel("Hz")
    ax[1].axhline(-SPEC["rl_min_db"], c="r", lw=.8); ax[1].grid(True, which="both", alpha=.3)
    ax[1].legend(fontsize=7)
    plt.tight_layout(); plt.savefig(f"diplexer_overview{SUF}.png", dpi=130)

    fig, ax = plt.subplots(figsize=(10, 4))
    hb = F >= 60e6
    for S, lab in [(S_sn, "ideal"), (S_re, "wirewound L1"), (S_co, "conical L1")]:
        ax.plot(F[hb] / 1e9, db(S[hb, 2, 0]), label=f"HP S31 {lab}")
    ax.set_ylim(-4, 0.5); ax.set_xlabel("GHz"); ax.set_ylabel("dB"); ax.grid(alpha=.3)
    ax.axhline(-SPEC["hp_il_max_db"], c="r", lw=.8); ax.legend(); ax.set_title("HP arm insertion loss, zoom")
    plt.tight_layout(); plt.savefig(f"diplexer_hp_zoom{SUF}.png", dpi=130)

    print(json.dumps({k: v for k, v in results.items() if k not in ("values", "parasitics", "spec")}, indent=1))
    print("LP snapped:", [f"{x:.3g}" for x in lp_s])
    print("HP snapped:", [f"{x:.3g}" for x in hp_s])
