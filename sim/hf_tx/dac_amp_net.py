"""DAC (AD9707 complementary current outputs) -> LMH6702 difference amplifier network.
Nodes: 1 A (IOUTA, RdA to gnd), 2 B (IOUTB, RdB to gnd), 3 N (-), 4 P (+), 5 OUT, 6 LOAD.
  B -Rg- N, N -Rf- OUT ;  A -R3- P, P -R4- gnd ;  OUT -50- LOAD -50- gnd
Excitation: IA = Ic + i, IB = Ic - i with Ic = IFS/2 (DC) and i = IFS/2 (full-scale sine amplitude).
Solved with the tested op-amp model in netsolve (ideal gain 1e6: network design, not bandwidth)."""
import sys, os, json, itertools
import numpy as np
from scipy.optimize import least_squares
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "diplexer"))
from netsolve import node_voltages, opamp

V_OUT_AMPL = 1.0          # V amplitude at amp output = 2.0 Vpp full scale
V_NODE_MAX = 1.0          # DAC node max (compliance 1.25 V, 0.25 V margin)
N = 7


def net(RdA, RdB, Rg, R3, R4, Rf):
    return [("R", 1, 0, RdA), ("R", 2, 0, RdB), ("R", 2, 3, Rg), ("R", 3, 5, Rf),
            ("R", 1, 4, R3), ("R", 4, 0, R4), ("R", 5, 6, 50.0), ("R", 6, 0, 50.0)] + opamp(5, 4, 3)


def analyse(r, Rf, ifs):
    el = net(*r, Rf)
    Vd = node_voltages(el, N, 1e6, {1: 1.0, 2: -1.0}).real        # per ampere of differential current
    Vc = node_voltages(el, N, 1e6, {1: 1.0, 2: 1.0}).real         # per ampere of common-mode current
    i = ic = ifs / 2
    peakA = ic * Vc[1] + i * abs(Vd[1]); peakB = ic * Vc[2] + i * abs(Vd[2])
    # noise gain for a CFB/VFB: 1 + Rf / R_seen_at_inverting_input (B node Thevenin = RdB)
    noise_gain = 1 + Rf / (r[2] + r[1])
    return {"vout_ampl_V": i * Vd[5], "cm_to_out_V_per_mA": Vc[5] * 1e-3, "dc_offset_out_V": ic * Vc[5],
            "swing_A_V": i * abs(Vd[1]), "swing_B_V": i * abs(Vd[2]), "peak_A_V": peakA, "peak_B_V": peakB,
            "noise_gain": noise_gain}


def resid(x, Rf, ifs):
    r = np.exp(x); a = analyse(r, Rf, ifs)
    return np.array([
        (a["vout_ampl_V"] - V_OUT_AMPL) * 10,
        a["dc_offset_out_V"] * 100,                                  # common mode must cancel
        (a["swing_A_V"] - a["swing_B_V"]) / max(a["swing_A_V"], 1e-6) * 10,   # balanced DAC loading
        max(0, a["peak_A_V"] - V_NODE_MAX) * 20, max(0, a["peak_B_V"] - V_NODE_MAX) * 20,
        0.05 * (a["noise_gain"] - 2.0),                              # mild preference: datasheet condition G=2
    ])


if __name__ == "__main__":
    lo, hi = np.log(np.full(5, 10.0)), np.log(np.full(5, 5000.0))
    rows = []
    for ifs, Rf in itertools.product([2e-3, 3e-3, 4e-3, 5e-3], [237.0, 300.0, 400.0, 500.0, 750.0]):
        best = None
        for start in ([200, 200, 120, 120, 237], [100, 100, 50, 50, 200], [400, 400, 300, 300, 600]):
            sol = least_squares(resid, np.log(start), args=(Rf, ifs), bounds=(lo, hi), max_nfev=400)
            if best is None or sol.cost < best.cost: best = sol
        r = np.exp(best.x); a = analyse(r, Rf, ifs)
        ok = (abs(a["vout_ampl_V"] - V_OUT_AMPL) < 0.01 and abs(a["dc_offset_out_V"]) < 1e-3 and
              abs(a["swing_A_V"] - a["swing_B_V"]) / a["swing_A_V"] < 0.01 and max(a["peak_A_V"], a["peak_B_V"]) <= V_NODE_MAX + 1e-3)
        rows.append({"IFS_mA": ifs * 1e3, "Rf": Rf, "feasible": bool(ok),
                     "RdA RdB Rg R3 R4": [round(v, 1) for v in r],
                     **{k: round(float(v), 4) for k, v in a.items()}})
    json.dump(rows, open(os.path.join(HERE, "dac_amp_net_results.json"), "w"), indent=1)
    for x in rows:
        print(f"IFS {x['IFS_mA']:.0f} mA  Rf {x['Rf']:4.0f}  {'OK ' if x['feasible'] else 'no '} "
              f"Vout {x['vout_ampl_V']:.3f}  off {x['dc_offset_out_V']*1e3:6.2f} mV  swing A/B {x['swing_A_V']:.3f}/{x['swing_B_V']:.3f}  "
              f"peak {max(x['peak_A_V'],x['peak_B_V']):.2f} V  NG {x['noise_gain']:.2f}  R {x['RdA RdB Rg R3 R4']}")
