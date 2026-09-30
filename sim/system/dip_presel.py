"""Diplexer (rev 2) + preselector (rev 1) simulated as ONE network.

Ports: 1 = antenna (diplexer common), 2 = LNA input (after selected preselector band),
3 = HP port (towards the AD9361 chain). All 50 ohm.
Reference: diplexer alone with its LP port terminated in 50 ohm.
The switch between diplexer LP port and preselector is modelled as a short 50-ohm trace."""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
for d in ("diplexer", "preselector", "hf_rx"):
    sys.path.insert(0, os.path.join(HERE, "..", d))
import real_parts as DIP
import preselector_ell as E, preselector as P
from netsolve import sparams, db, loss_worst, rl_worst

DIP_L = ('0805HP-271', '0805HP-271', '0805HP-56N', '0805HP-82N', '0805HP-101')
DIP_C = np.array([82, 62, 33, 30, 110]) * 1e-12


def combined(band, src=None):
    el_d, ports_d, nn_d = DIP.build_real(DIP_L, DIP_C)
    (com, _), (lp, _), (hp, _) = ports_d
    path = src or os.path.join(HERE, "..", "preselector", f"ell_{band}.json")
    j = json.load(open(path))
    el_p, ports_p, nn_p = E.build(np.array(j["values"]), ("parts", j["inductors"]))
    (p_in, _), (p_out, _) = ports_p
    off = nn_d - 2                                          # preselector node k>=2 -> k + off (node 1 -> diplexer LP port)
    remap = lambda n: 0 if n == 0 else (lp if n == p_in else n + off)
    el = list(el_d) + [(k, remap(a), remap(b), v) for k, a, b, v in el_p]
    return el, [(com, 50.0), (remap(p_out), 50.0), (hp, 50.0)], nn_p + off


def presel_alone(band, F):
    j = json.load(open(os.path.join(HERE, "..", "preselector", f"ell_{band}.json")))
    return E.sim(np.array(j["values"]), ("parts", j["inductors"]), F)


if __name__ == "__main__":
    F = np.logspace(np.log10(0.3e6), np.log10(6e9), 1800)
    ref = DIP.sim(DIP_L, DIP_C, F)                          # diplexer alone, LP port = 50 ohm
    out = {}
    for band in ("B1", "B2", "B3"):
        el, ports, nn = combined(band)
        S = sparams(el, ports, F, nn)
        fl, fh = P.BANDS[band]
        # 1) HP arm vs reference
        hpz = (F >= 67e6) & (F <= 6e9)
        d_hp = db(S[hpz, 2, 0]) - db(ref[hpz, 2, 0])
        worst_hp = loss_worst(S[hpz, 2, 0])
        k = np.argmax(np.abs(d_hp))
        # 2) antenna match
        rl_hp = rl_worst(S[hpz, 0, 0]); rl_hp_ref = rl_worst(ref[hpz, 0, 0])
        inb = (F >= fl) & (F <= fh)
        rl_band = rl_worst(S[inb, 0, 0])
        # 3) HF path: combined vs product of the isolated responses
        Sp = presel_alone(band, F)
        prod = db(ref[:, 1, 0]) + db(Sp[:, 1, 0])
        ripple = db(S[inb, 1, 0]) - prod[inb]
        # 4) IIP2_eff on the TRUE chain response
        S2 = np.zeros((len(F), 2, 2), complex); S2[:, 1, 0] = S[:, 1, 0]
        Fm = F[F <= 200e6]; S2m = S2[F <= 200e6]
        m = P.iip2_map(S2m, Fm, fl, fh)
        out[band] = {
            "HP_arm_max_change_dB": round(float(d_hp[k]), 2), "at_MHz": round(float(F[hpz][k] / 1e6), 1),
            "HP_arm_worst_IL_67M_6G_dB": round(worst_hp, 2),
            "HP_arm_worst_IL_ref_dB": round(loss_worst(ref[hpz, 2, 0]), 2),
            "antenna_RL_HP_band_dB": round(rl_hp, 1), "antenna_RL_HP_band_ref_dB": round(rl_hp_ref, 1),
            "antenna_RL_in_presel_band_dB": round(rl_band, 1),
            "HF_path_interaction_ripple_dB": [round(float(ripple.min()), 2), round(float(ripple.max()), 2)],
            "IIP2_eff_true_chain_dBm": min(m["sum"]["IIP2_eff_dBm"], m["diff"]["IIP2_eff_dBm"]),
        }
        np.save(os.path.join(HERE, f"_S_{band}.npy"), S)
    np.save(os.path.join(HERE, "_S_ref.npy"), ref); np.save(os.path.join(HERE, "_F.npy"), F)
    json.dump(out, open(os.path.join(HERE, "dip_presel_results.json"), "w"), indent=1)
    for b, o in out.items(): print(b, o)
