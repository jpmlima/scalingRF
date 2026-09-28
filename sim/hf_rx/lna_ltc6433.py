"""LTC6433-15 in the HF LNA path: noise (datasheet NF vs f) and 2nd/3rd-order intermod
at the receiver's own full scale. Datasheet: LTC6433-15 rev A (643315f), A-grade typicals."""
import json, numpy as np
import lineup as L

# datasheet NF / OIP3 / HD2 vs frequency (A-grade typ)
DS_F = np.array([0.1, 1, 10, 50, 100]); DS_NF = np.array([6.67, 3.93, 3.65, 2.92, 3.10])
G = 15.9; OIP3_10M = 47.6; HD2_10M_dBc, HD2_POUT = -54.0, 6.0

# ---- 2nd-order intercept estimated from HD2 ----
oip2_hd = HD2_POUT - HD2_10M_dBc          # HD2-referred intercept
oip2_im = oip2_hd - 6.0                   # IM2 (f1+f2) intercept ~6 dB lower than HD2-referred
iip2 = oip2_im - G; iip3 = OIP3_10M - G

# ---- scenario: two signals, each 6 dB below LNA-mode full scale (-19 dBm at antenna port) ----
FS_ANT = -19.0; LOSS_TO_LNA = 0.6          # diplexer + one switch, ~10-30 MHz
p_in = FS_ANT - 6 - LOSS_TO_LNA            # per tone at LNA input
im2_in = 2 * p_in - iip2                   # input-referred IM2 product
im3_in = 3 * p_in - 2 * iip3
nf_sys = 7.4                               # LNA mode, ~20 MHz (modes.py)
mds_2k4 = -174 + nf_sys + 10 * np.log10(2400)
iip2_needed = 2 * p_in - mds_2k4           # IM2 product at the noise floor in 2.4 kHz

res = {"LTC6433_A": {"G_dB": G, "IIP3_dBm_10MHz": round(iip3, 1), "OIP2_from_HD2_dBm": oip2_hd,
                     "IIP2_IM2_est_dBm": round(iip2, 1)},
       "scenario_tone_at_LNA_dBm": round(p_in, 1),
       "IM3_input_referred_dBm": round(im3_in, 1), "IM2_input_referred_dBm": round(im2_in, 1),
       "MDS_2k4_dBm": round(mds_2k4, 1),
       "IM3_margin_below_MDS_dB": round(mds_2k4 - im3_in, 1),
       "IM2_above_MDS_dB": round(im2_in - mds_2k4, 1),
       "IIP2_needed_without_preselection_dBm": round(iip2_needed, 1)}

# ---- system NF with the real LTC6433 NF curve + sub-octave preselector (loss assumed 1.0 dB) ----
import modes as M
PRESEL_DB = 1.0
f = M.f
nf_lna = np.interp(f, DS_F, DS_NF)
out = {}
for label, presel in [("no preselector", 0.0), ("with preselector 1.0 dB", PRESEL_DB)]:
    l_pre = M.dip + M.SW + presel
    l_post = M.SW + 0 + M.SW + M.aaf
    f_post = M.db2lin(l_post + M.nf_b)
    nf = 10 * np.log10(M.db2lin(l_pre) * (M.db2lin(nf_lna) + (f_post - 1) / M.db2lin(G)))
    gal = [None if ff < 10 else round(float(10 * np.log10((M.db2lin(L.fa("galactic", ff)) + M.db2lin(n) - 1) / M.db2lin(L.fa("galactic", ff)))), 1) for ff, n in zip(f, nf)]
    out[label] = {"f_MHz": f.tolist(), "NF_dB": np.round(nf, 1).tolist(), "desense_galactic_dB": gal}
res["system_LNA_mode"] = out
json.dump(res, open("lna_ltc6433_results.json", "w"), indent=1)
print(json.dumps(res, indent=1))
