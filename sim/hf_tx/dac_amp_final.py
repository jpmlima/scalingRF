"""Chosen network (IFS 5 mA, E96 values from the joint search in dac_amp_e96.py): verify nominal and Monte Carlo on resistor tolerance.
R4 is DNP (the optimiser pushed it to its 5 kohm bound = not needed); modelled as 1 Gohm."""
import os, json
import numpy as np
import dac_amp_net as N

IFS = 5e-3
E96 = {"RdA": 133.0, "RdB": 412.0, "Rg": 392.0, "R3": 10.0, "R4": 1e9, "Rf": 383.0}   # from dac_amp_e96.py


def run(v):
    return N.analyse([v["RdA"], v["RdB"], v["Rg"], v["R3"], v["R4"]], v["Rf"], IFS)


if __name__ == "__main__":
    nom = run(E96)
    res = {"values_ohm": {k: (v if v < 1e8 else "DNP") for k, v in E96.items()},
           "nominal": {k: round(float(x), 4) for k, x in nom.items()}}
    rng = np.random.default_rng(3)
    for tol in (0.001, 0.01):
        g, off, bal, pk = [], [], [], []
        for _ in range(2000):
            v = {k: (x * (1 + rng.uniform(-tol, tol)) if x < 1e8 else x) for k, x in E96.items()}
            a = run(v)
            g.append(a["vout_ampl_V"]); off.append(a["dc_offset_out_V"])
            bal.append((a["swing_A_V"] - a["swing_B_V"]) / a["swing_A_V"]); pk.append(max(a["peak_A_V"], a["peak_B_V"]))
        res[f"MC_tol_{tol*100:g}%"] = {
            "gain_spread_dB": [round(20 * np.log10(min(g) / nom["vout_ampl_V"]), 3), round(20 * np.log10(max(g) / nom["vout_ampl_V"]), 3)],
            "cm_offset_out_mV_max_abs": round(1e3 * float(np.max(np.abs(off))), 2),
            "balance_error_max_%": round(100 * float(np.max(np.abs(bal))), 2),
            "peak_DAC_node_max_V": round(float(max(pk)), 3)}
    json.dump(res, open(os.path.join(N.HERE, "dac_amp_final.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
