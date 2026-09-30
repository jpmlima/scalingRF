"""
scalingRF — HF TX lineup: AD9707 (150 MSPS) -> DC-coupled diff-to-SE amplifier (back-terminated)
-> reconstruction LPF (50 ohm) -> switch -> diplexer LP arm -> TX port.

Questions: level plan to ~0 dBm at the port, image rejection needed from the reconstruction
filter (the diplexer LP arm already rejects part of it), sinc droop, in-band harmonics,
and the resulting requirements for the amplifier and the filter.

Data: AD9707 datasheet (IOUTFS 1-5 mA, compliance -1..+1.25 V, SFDR 84/83/75 dBc @5/10/20 MHz,
NSD ~-150 dBc/Hz); diplexer rev 2 (sim/diplexer, real Coilcraft models).
"""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "diplexer"))
import real_parts as DIP
from netsolve import db

FS = 150e6
P_PORT_DBM = 0.0                 # target at the TX port
SPUR_TARGET_DBC = -60.0          # images / out-of-band spurs at the port
SW_DB = 0.3                      # switch (ASSUMED, same as RX)
RECON_PASS_DB = 1.0              # reconstruction filter passband loss (ASSUMED, to be designed)

DIP_L = ('0805HP-271', '0805HP-271', '0805HP-56N', '0805HP-82N', '0805HP-101')
DIP_C = np.array([82, 62, 33, 30, 110]) * 1e-12


def sinc_db(f):
    x = np.pi * f / FS
    return 20 * np.log10(np.abs(np.sin(x) / x))


def image_dbc(f):
    """First image (fs - f) relative to the wanted tone, zero-order hold only.
    sin(pi(fs-f)/fs) = sin(pi f/fs), so the ratio is f/(fs-f)."""
    return 20 * np.log10(f / (FS - f))


if __name__ == "__main__":
    out = {}
    # ---- diplexer LP arm attenuation at the image frequencies (real model)
    f_out = np.array([1e6, 5e6, 10e6, 20e6, 30e6, 40e6, 45e6, 49e6])
    f_img = FS - f_out
    F = np.unique(np.concatenate([f_out, f_img]))
    S = DIP.sim(DIP_L, DIP_C, F)
    dip = dict(zip(F, -db(S[:, 1, 0])))
    rows = []
    for f, fi in zip(f_out, f_img):
        img = image_dbc(f)
        dip_rel = dip[fi] - dip[f]                      # extra diplexer rejection at the image vs at the tone
        need = max(0.0, img - dip_rel - SPUR_TARGET_DBC)    # extra rejection the recon filter must add
        rows.append({"f_MHz": f / 1e6, "image_MHz": fi / 1e6, "image_dBc_ZOH": round(img, 1),
                     "diplexer_rel_rej_dB": round(dip_rel, 1), "recon_rej_needed_dB": round(need, 1),
                     "sinc_droop_dB": round(sinc_db(f), 2)})
    out["images"] = rows
    worst = max(rows, key=lambda r: r["recon_rej_needed_dB"])

    # ---- level plan (worst case = top of band)
    dip_loss_49 = dip[49e6]
    p_amp_out = P_PORT_DBM + dip_loss_49 + SW_DB + RECON_PASS_DB           # into a 50-ohm filter
    v_load_pp = 2 * np.sqrt(2 * 50 * 10 ** (p_amp_out / 10) / 1000)        # Vpp across the 50-ohm load
    v_amp_pp = 2 * v_load_pp                                               # back-terminated (50-ohm series)
    iout_fs = 2e-3; r_dac = 50.0                                           # 2 mA into 50 ohm per side
    v_dac_diff_pp = 2 * iout_fs * r_dac                                    # complementary outputs
    comp_ok = iout_fs * r_dac <= 1.25
    sinc49 = -sinc_db(49e6)
    gain_needed_db = 20 * np.log10(v_amp_pp / v_dac_diff_pp) + sinc49      # amp gain incl. droop at 49 MHz
    out["level_plan"] = {
        "diplexer_LP_loss_at_49MHz_dB": round(dip_loss_49, 2),
        "amp_output_power_into_filter_dBm": round(p_amp_out, 2),
        "amp_output_Vpp_open_circuit_equiv": round(v_amp_pp, 2),
        "DAC": {"IOUTFS_mA": 2, "R_per_side_ohm": r_dac, "diff_Vpp": round(v_dac_diff_pp, 2),
                "per_side_max_V": iout_fs * r_dac, "within_compliance_+1.25V": bool(comp_ok)},
        "amp_gain_needed_dB (diff->SE, incl. 1.6 dB sinc at 49 MHz unless compensated in PL)": round(gain_needed_db, 1),
        "amp_gain_needed_dB_if_sinc_compensated_in_PL": round(gain_needed_db - sinc49, 1)}
    out["recon_filter_requirement"] = {
        "passband": "DC-49 MHz, loss <= 1 dB (assumed in level plan)",
        "worst_case": worst,
        "rejection_needed_at_101MHz_dB": worst["recon_rej_needed_dB"],
        "note": "image rejection is shared with the diplexer LP arm; the filter only needs the difference"}
    out["in_band_harmonics"] = {
        "tones_with_in_band_harmonics": "<= 24.5 MHz (2nd harmonic <= 49 MHz)",
        "AD9707_SFDR_dBc": {"5 MHz": 84, "10 MHz": 83, "20 MHz": 75},
        "amp_requirement": "HD2/HD3 <= -75 dBc up to 24.5 MHz at full output, so the amplifier does not dominate the DAC",
        "tones_above_24.5MHz": "harmonics >= 50 MHz: filtered by recon filter + diplexer LP arm",
        "gap": "AD9707 SFDR not specified above 20 MHz (non-harmonic spurs 20-49 MHz unknown)"}
    json.dump(out, open(os.path.join(HERE, "lineup_results.json"), "w"), indent=1)
    for r in rows: print(r)
    print(json.dumps(out["level_plan"], indent=1))
    print("recon filter must add", worst["recon_rej_needed_dB"], "dB at", worst["image_MHz"], "MHz")
