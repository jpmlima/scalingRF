"""Joint discrete search over E96 neighbours (R3 = 10 ohm, R4 DNP) for balance, CM offset and gain."""
import os, json, itertools
import numpy as np
import dac_amp_net as N

IFS = 5e-3
E96 = np.array([1.00,1.02,1.05,1.07,1.10,1.13,1.15,1.18,1.21,1.24,1.27,1.30,1.33,1.37,1.40,1.43,1.47,1.50,1.54,1.58,
                1.62,1.65,1.69,1.74,1.78,1.82,1.87,1.91,1.96,2.00,2.05,2.10,2.15,2.21,2.26,2.32,2.37,2.43,2.49,2.55,
                2.61,2.67,2.74,2.80,2.87,2.94,3.01,3.09,3.16,3.24,3.32,3.40,3.48,3.57,3.65,3.74,3.83,3.92,4.02,4.12,
                4.22,4.32,4.42,4.53,4.64,4.75,4.87,4.99,5.11,5.23,5.36,5.49,5.62,5.76,5.90,6.04,6.19,6.34,6.49,6.65,
                6.81,6.98,7.15,7.32,7.50,7.68,7.87,8.06,8.25,8.45,8.66,8.87,9.09,9.31,9.53,9.76])


def around(x, n=4):
    e = 10 ** np.floor(np.log10(x)); vals = np.concatenate([E96 * e / 10, E96 * e, E96 * e * 10])
    return vals[np.argsort(np.abs(np.log(vals / x)))[:n]]


best = []
for RdA, RdB, Rg, Rf in itertools.product(around(137.2, 6), around(399.7), around(400.3), around(400.0)):
    a = N.analyse([RdA, RdB, Rg, 10.0, 1e9], Rf, IFS)
    bal = abs(a["swing_A_V"] - a["swing_B_V"]) / a["swing_A_V"]
    cost = abs(a["dc_offset_out_V"]) * 1e3 / 1.0 + bal * 100 / 0.5 + abs(a["vout_ampl_V"] - 1.0) * 100 / 1.0 \
           + 50 * max(0, max(a["peak_A_V"], a["peak_B_V"]) - 1.0)
    best.append((cost, RdA, RdB, Rg, Rf, a, bal))
best.sort(key=lambda t: t[0])
c, RdA, RdB, Rg, Rf, a, bal = best[0]
out = {"values_ohm": {"RdA": RdA, "RdB": RdB, "Rg": Rg, "R3": 10.0, "R4": "DNP", "Rf": Rf},
       "vout_ampl_V": round(a["vout_ampl_V"], 4), "cm_offset_mV": round(a["dc_offset_out_V"] * 1e3, 2),
       "balance_error_%": round(bal * 100, 2), "peak_DAC_node_V": round(max(a["peak_A_V"], a["peak_B_V"]), 3),
       "noise_gain": round(a["noise_gain"], 2)}
json.dump(out, open(os.path.join(N.HERE, "dac_amp_e96.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
