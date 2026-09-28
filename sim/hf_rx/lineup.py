"""
scalingRF — HF RX lineup: antenna port -> limiter -> diplexer LP -> switches/attenuator
-> anti-alias filter (50 ohm) -> LTC6409 FDA (DC-coupled, single-ended in) -> RC -> LTC2262-14.

Questions: noise figure, full-scale input level, and whether the receiver or the
external (antenna) noise sets sensitivity across 1 kHz - 49 MHz.

Sources (see README): LTC6409 datasheet rev B (en, in, noise equations, Fig. 7, front-page
application with LTC2262-14), LTC2261-14 datasheet rev C, LTC2262-14 SNR 72.8 dB,
ITU-R P.372 median man-made / galactic noise.
"""
import json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

K4T = 4 * 1.380649e-23 * 290.0          # 4kT0, V^2/Hz/ohm
def en_r(r): return np.sqrt(K4T * r)
def par(a, b):
    if not np.isfinite(a): return b
    if not np.isfinite(b): return a
    return a * b / (a + b)

# ---------------- ADC: LTC2262-14 @150 Msps, 2 Vpp range ----------------
FS = 150e6
ADC_SNR_DB = 72.8
ADC_VFS_RMS = 2.0 / 2 / np.sqrt(2)                  # 2 Vpp differential sine -> 0.707 Vrms
ADC_VN_RMS = ADC_VFS_RMS / 10 ** (ADC_SNR_DB / 20)
ADC_EN = ADC_VN_RMS / np.sqrt(FS / 2)               # equivalent white density at ADC input

# ---------------- FDA: LTC6409 ----------------
ENI, INI = 1.1e-9, 8.8e-12


def fda(RI, RF, RT, RS=50.0):
    """LTC6409 datasheet noise model (Fig. 6 equations). Returns
    (eno excluding RS [V/rtHz], eno from RS [V/rtHz], voltage gain source-EMF -> diff out)."""
    rts = par(RT, RS)
    a = ENI * (1 + RF / (RI + rts / 2))
    b2 = 2 * (INI * RF) ** 2
    c = en_r(RI) * RF / (RI + rts / 2)
    d2 = 2 * en_r(RF) ** 2
    e = en_r(RT) * (RF / RI) * par(2 * RI, RS) / (RT + par(2 * RI, RS)) if np.isfinite(RT) else 0.0
    eno2 = a ** 2 + b2 + 2 * c ** 2 + d2 + e ** 2
    gv = (RF / RI) * par(2 * RI, RT) / (RS + par(2 * RI, RT))
    eno_rs = en_r(RS) * gv
    return np.sqrt(eno2), eno_rs, gv


def matched_rt(RI, RF, RS=50.0):
    """Single-ended input impedance of the FDA (datasheet) and the shunt RT that makes it RS."""
    rin = RI / (1 - 0.5 * RF / (RI + RF))
    return rin * RS / (rin - RS), rin


def back_end(RI, RF, RT, enbw_fda):
    """FDA + ADC seen from a 50-ohm source. Returns NF [dB], full-scale available input power [dBm]."""
    eno, eno_rs, gv = fda(RI, RF, RT)
    # FDA wideband noise folds into the ADC Nyquist band in proportion to its noise bandwidth
    fold = enbw_fda / (FS / 2)
    n_out = eno ** 2 * fold + ADC_EN ** 2          # per Hz, referred to ADC input
    nf = 10 * np.log10(1 + n_out / eno_rs ** 2)
    vs_fs = ADC_VFS_RMS / gv                         # source EMF (rms) that fills the ADC
    p_fs = 10 * np.log10(vs_fs ** 2 / (4 * 50) / 1e-3)
    return nf, p_fs, dict(eno_nV=eno * 1e9, eno_rs_nV=eno_rs * 1e9, gain_vv=gv)


# ---------------- validation against the datasheet measurement ----------------
def validate():
    """LTC6409 front page: RI=RF=150, single-ended 50-ohm source, no termination,
    output 1.8 Vpp into LTC2262-14 @150 Msps, 70 MHz: measured SNR 71.1 dB."""
    eno, eno_rs, _ = fda(150, 150, np.inf)
    adc_snr_70 = ADC_SNR_DB - 0.2                     # datasheet family: -0.2 dB from 5 to 70 MHz
    en_adc = ADC_VFS_RMS / 10 ** (adc_snr_70 / 20) / np.sqrt(FS / 2)
    out = {}
    for enbw in (100e6, 200e6):
        n = np.sqrt(en_adc ** 2 * FS / 2 + (eno ** 2 + eno_rs ** 2) * enbw)
        snr_dbfs = 20 * np.log10(ADC_VFS_RMS / n)
        out[f"enbw_{int(enbw/1e6)}MHz"] = round(snr_dbfs - 20 * np.log10(2.0 / 1.8), 2)
    out["measured"] = 71.1
    return out


# ---------------- front-end losses before the FDA (dB) ----------------
F_MHZ = np.array([0.001, 0.5, 1.8, 3.5, 7, 10, 14, 21, 28, 40, 49])
DIPLEXER_DB = np.interp(F_MHZ, [0.001, 10, 30, 49], [0.14, 0.27, 0.5, 1.0])   # sim/diplexer rev 2
SWITCHES_DB = 0.6        # bias-tee DC-block path + attenuator path, CMOS switches (ASSUMED)
AAF_DB = np.interp(F_MHZ, [0.001, 30, 49], [0.3, 0.5, 0.9])                   # to be designed (ASSUMED)
L_PRE = DIPLEXER_DB + SWITCHES_DB + AAF_DB

# ---------------- ITU-R P.372 median external noise Fa = c - d log10(f_MHz) ----------------
ITU = {"city": (76.8, 27.7), "residential": (72.5, 27.7), "rural": (67.2, 27.7),
       "quiet rural": (53.6, 28.6), "galactic": (52.0, 23.0)}
def fa(env, f):
    c, d = ITU[env]; return c - d * np.log10(f)


if __name__ == "__main__":
    res = {"validation_snr_dB": validate(), "adc_en_nV": round(ADC_EN * 1e9, 2)}
    configs = {}
    for av, (ri, rf) in {"AV1": (150, 150), "AV2": (100, 200), "AV5": (50, 250), "AV10": (50, 500)}.items():
        rt, rin = matched_rt(ri, rf)
        for enbw in (100e6,):
            nf_b, pfs_b, det = back_end(ri, rf, rt, enbw)
        configs[av] = {"RI": ri, "RF": rf, "RT_match": round(rt, 1), "Rin_fda": round(rin, 1),
                       "backend_NF_dB": round(nf_b, 2), "backend_FS_dBm": round(pfs_b, 2),
                       **{k: round(v, 3) for k, v in det.items()}}
    res["backend"] = configs

    # system at the antenna port, attenuator 0 dB, per gain option
    fz = F_MHZ[F_MHZ >= 0.5]; lz = L_PRE[F_MHZ >= 0.5]
    sysres = {}
    for av, c in configs.items():
        nf = lz + c["backend_NF_dB"]; fsd = lz + c["backend_FS_dBm"]
        sysres[av] = {"f_MHz": fz.tolist(), "NF_dB": np.round(nf, 1).tolist(),
                      "FS_dBm": np.round(fsd, 1).tolist(),
                      "noise_floor_dBm_Hz": np.round(-174 + nf, 1).tolist()}
        # degradation of external-noise-limited sensitivity (lossless antenna)
        for env in ITU:
            if env == "galactic":
                mask = fz >= 10    # galactic noise reaches the ground only above ~ionospheric cutoff
            else:
                mask = np.ones_like(fz, bool)
            fa_lin = 10 ** (fa(env, fz) / 10); frx = 10 ** (nf / 10)
            deg = 10 * np.log10((fa_lin + frx - 1) / fa_lin)
            sysres[av][f"desense_{env}_dB"] = [round(x, 1) if m else None for x, m in zip(deg, mask)]
    res["system_att0"] = sysres
    res["assumptions"] = {"switch_path_loss_dB": SWITCHES_DB, "aaf_loss_dB": "0.3 -> 0.9 (not yet designed)",
                          "fda_noise_bw_Hz": 100e6, "diplexer": "sim/diplexer rev 2"}
    json.dump(res, open("lineup_results.json", "w"), indent=1)

    # --- plot: NF vs external noise
    fig, ax = plt.subplots(figsize=(10, 6))
    ff = np.logspace(np.log10(0.5), np.log10(49), 200)
    for env, ls in [("residential", "-"), ("rural", "--"), ("quiet rural", ":"), ("galactic", "-.")]:
        m = ff >= (10 if env == "galactic" else 0)
        ax.semilogx(ff[m], fa(env, ff[m]), ls, c="gray", label=f"Fa {env} (ITU-R P.372)")
    for av in configs:
        ax.semilogx(fz, sysres[av]["NF_dB"], "o-", label=f"scalingRF NF, {av}, att 0 dB")
    ax.set_xlabel("MHz"); ax.set_ylabel("dB above kT0"); ax.grid(True, which="both", alpha=.3)
    ax.set_title("HF RX: receiver noise figure vs external noise at the antenna"); ax.legend(fontsize=8)
    plt.tight_layout(); plt.savefig("hf_nf_vs_external_noise.png", dpi=130)

    print(json.dumps(res["validation_snr_dB"]), "ADC en %.1f nV/rtHz" % (ADC_EN * 1e9))
    for av, c in configs.items():
        print(av, c)
    for av in configs:
        s = sysres[av]
        print(f"\n{av}: f(MHz)      ", s["f_MHz"])
        print("   NF (dB)     ", s["NF_dB"]); print("   FS (dBm)    ", s["FS_dBm"])
        for env in ("residential", "rural", "quiet rural", "galactic"):
            print(f"   desense {env:12s}", s[f"desense_{env}_dB"])
