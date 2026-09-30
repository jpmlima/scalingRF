"""Gain modes with fixed FDA gain (AV5) + switchable LNA path + 0/10/20 dB attenuator.
LNA values are REQUIREMENTS to be met by a part, not a selected part."""
import json, numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import lineup as L

LNA_NF, LNA_G = 2.0, 16.0            # requirement candidates
SW = 0.3                              # one CMOS/SOI switch pass (ASSUMED)
f = L.F_MHZ[L.F_MHZ >= 0.5]
dip = np.interp(f, [0.001, 10, 30, 49], [0.14, 0.27, 0.5, 1.0])
aaf = np.interp(f, [0.001, 30, 49], [0.3, 0.5, 0.9])
rt, _ = L.matched_rt(50, 250)
nf_b, fs_b, _ = L.back_end(50, 250, rt, 100e6)          # AV5 back end

def db2lin(x): return 10 ** (np.asarray(x) / 10)

def mode(lna, att):
    # chain: diplexer -> SW -> [LNA or bypass] -> SW -> attenuator(SW-selected) -> AAF -> FDA+ADC
    l_pre = dip + SW                                  # before LNA
    l_post = SW + att + SW + aaf                      # after LNA (incl. attenuator path)
    f_post = db2lin(l_post + nf_b)
    if lna:
        fsys = db2lin(l_pre) * (db2lin(LNA_NF) + (f_post - 1) / db2lin(LNA_G))
        fs = l_pre - LNA_G + l_post + fs_b
    else:
        fsys = db2lin(l_pre) * f_post
        fs = l_pre + l_post + fs_b
    return 10 * np.log10(fsys), fs


if __name__ == "__main__":
    out = {"f_MHz": f.tolist(), "backend_AV5_NF_dB": round(nf_b, 2), "backend_AV5_FS_dBm": round(fs_b, 2),
           "LNA_requirement": {"NF_dB": LNA_NF, "gain_dB": LNA_G}}
    fig, ax = plt.subplots(figsize=(10, 6))
    ff = np.logspace(np.log10(0.5), np.log10(49), 200)
    for env, ls in [("residential", "-"), ("rural", "--"), ("quiet rural", ":"), ("galactic", "-.")]:
        m = ff >= (10 if env == "galactic" else 0)
        ax.semilogx(ff[m], L.fa(env, ff[m]), ls, c="gray", label=f"Fa {env}")
    for name, lna, att in [("LNA on, att 0", True, 0), ("bypass, att 0", False, 0),
                           ("bypass, att 10", False, 10), ("bypass, att 20", False, 20)]:
        nf, fs = mode(lna, att)
        gal = np.where(f >= 10, 10 * np.log10((db2lin(L.fa("galactic", f)) + db2lin(nf) - 1) / db2lin(L.fa("galactic", f))), np.nan)
        qr = 10 * np.log10((db2lin(L.fa("quiet rural", f)) + db2lin(nf) - 1) / db2lin(L.fa("quiet rural", f)))
        out[name] = {"NF_dB": np.round(nf, 1).tolist(), "FS_dBm": np.round(fs, 1).tolist(),
                     "desense_galactic_dB": [None if np.isnan(x) else round(float(x), 1) for x in gal],
                     "desense_quiet_rural_dB": np.round(qr, 1).tolist()}
        ax.semilogx(f, nf, "o-", label=f"NF: {name}")
        print(f"{name:16s} NF {np.round(nf,1)}\n{'':16s} FS {np.round(fs,1)}\n{'':16s} desense galactic {out[name]['desense_galactic_dB']}\n{'':16s} desense quiet rural {out[name]['desense_quiet_rural_dB']}")

    # LNA linearity requirement: two tones at FS-6 dB each at the LNA input,
    # IMD3 at least 90 dBc down (below ADC SFDR ~88 dB)
    fs_lna = mode(True, 0)[1].max()
    p_tone = fs_lna - 6
    iip3_req = p_tone + 90 / 2
    out["LNA_requirement"].update({"IIP3_dBm_min": round(float(iip3_req), 1), "OIP3_dBm_min": round(float(iip3_req + LNA_G), 1),
                                   "band": "1-50 MHz, AC-coupled, bypass path used below that"})
    print("LNA requirement:", out["LNA_requirement"])
    ax.set_xlabel("MHz"); ax.set_ylabel("dB above kT0"); ax.grid(True, which="both", alpha=.3); ax.legend(fontsize=8)
    ax.set_title("HF RX gain modes (FDA fixed AV5) vs external noise")
    plt.tight_layout(); plt.savefig("hf_modes_vs_external_noise.png", dpi=130)
    json.dump(out, open("modes_results.json", "w"), indent=1)
