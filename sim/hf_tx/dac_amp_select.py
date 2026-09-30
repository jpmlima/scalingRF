"""Pick a DAC->LMH6702 network among the feasible solutions of dac_amp_net.py:
- distortion: first-order CFB estimate HD(Rf) = HD(237) + 20 log10(Rf/237) (loop gain ~ Z/Rf) — an
  approximation, the datasheet has no HD-vs-Rf data;
- output noise vs the DAC's own NSD (-150 dBc/Hz), LMH6702: en 1.83 nV, inverting in 18.5 pA, non-inv 3.0 pA;
- DC output offset (datasheet max VIO 4.5 mV, IBI 30 uA, IBN 15 uA)."""
import os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
K4T = 4 * 1.380649e-23 * 290
EN, IN_INV, IN_NON = 1.83e-9, 18.5e-12, 3.0e-12
HD2_28M_237, HD3_28M_237 = -73.0, -82.0      # SOT-23, extrapolated from 20 MHz (rev 1): 12 / 18 dB per octave
REQ = -65.0
V_FS_RMS = 1.0 / np.sqrt(2)                  # 2.0 Vpp full scale at the amp output

rows = json.load(open(os.path.join(HERE, "dac_amp_net_results.json")))
out = []
for r in rows:
    if not r["feasible"]: continue
    RdA, RdB, Rg, R3, R4 = r["RdA RdB Rg R3 R4"]; Rf = r["Rf"]
    ng = r["noise_gain"]
    r_inv = Rg + RdB                                    # source resistance seen by the inverting input
    r_non = 1 / (1 / (R3 + RdA) + 1 / R4) if R4 < 1e5 else R3 + RdA
    e2 = (EN * ng) ** 2 + (IN_INV * Rf) ** 2 + (IN_NON * r_non * ng) ** 2 \
         + K4T * Rf + K4T * r_inv * (Rf / r_inv) ** 2 + K4T * r_non * ng ** 2
    en_out = np.sqrt(e2)
    dbc_hz = 20 * np.log10(en_out / V_FS_RMS)
    hd_pen = 20 * np.log10(Rf / 237.0)
    hd2, hd3 = HD2_28M_237 + hd_pen, HD3_28M_237 + hd_pen
    off = (4.5e-3 + 15e-6 * r_non) * ng + 30e-6 * Rf    # worst-case, datasheet max
    out.append({"IFS_mA": r["IFS_mA"], "Rf": Rf, "noise_gain": round(ng, 2),
                "peak_DAC_node_V": round(max(r["peak_A_V"], r["peak_B_V"]), 2),
                "amp_out_noise_nV": round(en_out * 1e9, 2), "amp_noise_dBc_Hz": round(dbc_hz, 1),
                "HD2_28MHz_est_dBc": round(hd2, 1), "HD3_28MHz_est_dBc": round(hd3, 1),
                "meets_HD_req": bool(max(hd2, hd3) <= REQ),
                "dc_offset_out_worst_mV": round(off * 1e3, 1), "R": r["RdA RdB Rg R3 R4"]})
json.dump(out, open(os.path.join(HERE, "dac_amp_select.json"), "w"), indent=1)
for o in out:
    print(o)
