"""VHF-6 GHz RX lineup: NF, IIP3 and SFDR for three LNA arrangements, vs external noise at low VHF.
Passive losses other than the diplexer are ASSUMPTIONS until parts are chosen."""
import sys, os, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "diplexer"))
import real_parts as DIP
from netsolve import db
from cascade import cascade, passive, lin, dbv

F = np.array([100e6, 145e6, 435e6, 900e6, 1.3e9, 2.4e9, 3.5e9, 5.8e9])
DIP_L = ('0805HP-271', '0805HP-271', '0805HP-56N', '0805HP-82N', '0805HP-101')
DIP_C = np.array([82, 62, 33, 30, 110]) * 1e-12

# ---- ASSUMED passive losses vs frequency (dB) — to be replaced by chosen parts
# pSemi PE42582 SP8T, ports RF1/RF8 (lowest loss; highest bands go there). Datasheet Table 3,
# band centres: <=0.1 / 0.1-1 / 1-2 / 2-4 / 4-6 GHz. SWITCH_CASE selects typical or maximum.
SW_F = [0.1e9, 0.55e9, 1.5e9, 3e9, 5e9, 6e9]
SW_TYP = [0.7, 0.8, 0.9, 0.9, 1.1, 1.1]
SW_MAX = [0.9, 1.0, 1.2, 1.5, 1.9, 1.9]
SWITCH_CASE = "typ"
def switch_loss(f): return np.interp(f, SW_F, SW_TYP if SWITCH_CASE == "typ" else SW_MAX)
def filter_loss(f): return np.interp(f, [1e8, 3e9, 6e9], [1.0, 1.0, 1.5])                 # bank passband
def balun_loss(f): return np.interp(f, [1e8, 3e9, 6e9], [0.8, 0.8, 1.5])                  # 10-6000 MHz class
LIMITER = 0.2

# ---- AD9361 at max gain (datasheet): NF 2/3/3.8 dB, IIP3 -18/-14/-17 dBm at 0.8/2.4/5.5 GHz
def ad_nf(f): return np.interp(f, [0.8e9, 2.4e9, 5.5e9], [2.0, 3.0, 3.8])
def ad_ip3(f): return np.interp(f, [0.8e9, 2.4e9, 5.5e9], [-18.0, -14.0, -17.0])

# ---- LNA: representative wideband target (to be confirmed/selected)
LNA = {"G": 12.0, "NF": 1.5, "OIP3": 33.0}          # net gain ~12 dB (rev 0 result)

def lineup(f, arrangement, dip_loss):
    lna = {"name": "LNA", "G": LNA["G"], "NF": LNA["NF"], "IIP3": LNA["OIP3"] - LNA["G"]}
    ad = {"name": "AD9361", "G": 60.0, "NF": float(ad_nf(f)), "IIP3": float(ad_ip3(f))}
    front = [passive("limiter", LIMITER), passive("diplexer HP", dip_loss)]
    sw, fl, bal = passive("switch", switch_loss(f)), passive("filter", filter_loss(f)), passive("balun", balun_loss(f))
    if arrangement == "A_filter_then_LNA": chain = front + [sw, fl, sw, lna, bal, ad]
    elif arrangement == "B_LNA_then_filter": chain = front + [lna, sw, fl, sw, bal, ad]
    else: chain = front + [sw, fl, sw, bal, ad]                      # C: LNA bypassed
    return cascade(chain)

if __name__ == "__main__":
    S = DIP.sim(DIP_L, DIP_C, F); dip = -db(S[:, 2, 0])
    out = {"assumptions": {"switch": "0.4-1.2 dB", "filter": "1.0-1.5 dB", "balun": "0.8-1.5 dB", "limiter": LIMITER,
                           "LNA_target": LNA, "AD9361": "datasheet max-gain NF/IIP3"}, "rows": []}
    for f, dl in zip(F, dip):
        row = {"f_MHz": f / 1e6, "diplexer_dB": round(float(dl), 2)}
        for arr in ("A_filter_then_LNA", "B_LNA_then_filter", "C_LNA_bypass"):
            r = lineup(f, arr, dl)
            mds_1m = -174 + r["NF_dB"] + 60
            row[arr] = {"NF": round(r["NF_dB"], 1), "IIP3": round(r["IIP3_dBm"], 1),
                        "SFDR_1MHz": round(2 / 3 * (r["IIP3_dBm"] - mds_1m), 1)}
        # external noise at the antenna (ITU-R P.372 medians) where it is still relevant
        fm = f / 1e6
        row["Fa_rural_dB"] = round(67.2 - 27.7 * np.log10(fm), 1)
        row["Fa_galactic_dB"] = round(52.0 - 23.0 * np.log10(fm), 1)
        out["rows"].append(row)
    json.dump(out, open(os.path.join(HERE, "vhf_lineup_results.json"), "w"), indent=1)
    print(f"{'f MHz':>7} {'dip':>5} | {'A: filt->LNA':>20} | {'B: LNA->filt':>20} | {'C: bypass':>20} | Fa rural/gal")
    for r in out["rows"]:
        fmt = lambda d: f"NF {d['NF']:4.1f} IP3 {d['IIP3']:6.1f} SFDR {d['SFDR_1MHz']:4.1f}"
        print(f"{r['f_MHz']:7.0f} {r['diplexer_dB']:5.2f} | {fmt(r['A_filter_then_LNA'])} | {fmt(r['B_LNA_then_filter'])} | {fmt(r['C_LNA_bypass'])} | {r['Fa_rural_dB']:5.1f}/{r['Fa_galactic_dB']:5.1f}")
