"""Option C (LNA bypass with two SPDTs) vs option D (LNA always on + digital step attenuator after it).
D removes the pre-LNA SPDT. DSA insertion loss ASSUMED 1.0 -> 2.0 dB (100 MHz -> 6 GHz) on top of its setting."""
import os, json
import numpy as np
import vhf_lineup as V, vhf_lineup_parts as P
from cascade import cascade, passive
from netsolve import db

def dsa_il(f): return float(np.interp(f, [1e8, 3e9, 6e9], [1.0, 1.4, 2.0]))     # ASSUMED

def chain_D(f, dip, case, setting):
    V.SWITCH_CASE = case
    pre = [passive("limiter", 0.2), passive("diplexer HP", dip), passive("SP8T in", V.switch_loss(f)),
           passive("filter", V.filter_loss(f)), passive("SP8T out", V.switch_loss(f))]
    st = pre + [P.hmc8410(f, case), passive("DSA", dsa_il(f) + setting), passive("balun", P.balun(f, case)),
                {"name": "AD9361", "G": 60.0, "NF": float(V.ad_nf(f)), "IIP3": float(V.ad_ip3(f))}]
    V.SWITCH_CASE = "typ"
    return cascade(st)

if __name__ == "__main__":
    S = V.DIP.sim(V.DIP_L, V.DIP_C, V.F); dip = -db(S[:, 2, 0])
    rows = []
    for f, d in zip(V.F, dip):
        set_norm = max(0.0, P.PAD - dsa_il(f))                 # keep the same net gain as the fixed 6 dB pad
        c_on, _ = P.chain(f, d, "typ", True); c_off, _ = P.chain(f, d, "typ", False)
        d_norm = chain_D(f, d, "typ", set_norm); d_strong = chain_D(f, d, "typ", set_norm + 20.0)
        rows.append({"f_MHz": f / 1e6,
                     "C_LNA_on": (round(c_on["NF_dB"], 1), round(c_on["IIP3_dBm"], 1)),
                     "C_bypass": (round(c_off["NF_dB"], 1), round(c_off["IIP3_dBm"], 1)),
                     "D_normal": (round(d_norm["NF_dB"], 1), round(d_norm["IIP3_dBm"], 1)),
                     "D_strong_+20dB": (round(d_strong["NF_dB"], 1), round(d_strong["IIP3_dBm"], 1))})
    json.dump(rows, open(os.path.join(V.HERE, "bypass_vs_dsa.json"), "w"), indent=1)
    print(f"{'f MHz':>6} | {'C: LNA on':>14} | {'C: bypass':>14} | {'D: normal':>14} | {'D: +20 dB':>14}   (NF dB, IIP3 dBm)")
    for r in rows:
        f = lambda t: f"{t[0]:4.1f} / {t[1]:6.1f}"
        print(f"{r['f_MHz']:6.0f} | {f(r['C_LNA_on'])} | {f(r['C_bypass'])} | {f(r['D_normal'])} | {f(r['D_strong_+20dB'])}")
