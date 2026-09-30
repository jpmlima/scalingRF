"""VHF-6 GHz RX lineup with selected parts and EVERY pass listed explicitly (lesson D20):
limiter -> diplexer HP -> SP8T in -> filter -> SP8T out -> SPDT (LNA/bypass) -> [HMC8410 -> pad] | [bypass]
-> SPDT -> balun (TCM1-63AX+) -> AD9361.  Typical and maximum (datasheet) cases.
Still ASSUMED: limiter 0.2 dB, filters 1.0-1.5 dB, LNA-bypass SPDTs 0.3-0.6 dB."""
import os, json
import numpy as np
import vhf_lineup as V                      # AD9361 data, diplexer, PE42582 tables
from cascade import cascade, passive
from netsolve import db

PAD = 6.0
def hmc8410(f, case):   # datasheet: 0.01-3 GHz G 19.5 (min 17.5), NF 1.1 (max 1.6, spec from 0.3 GHz); 3-8 GHz G 18 (15.5), NF 1.4 (1.9); OIP3 33
    lo = f < 3e9
    g = (19.5 if lo else 18.0) if case == "typ" else (17.5 if lo else 15.5)
    nf = (1.1 if lo else 1.4) if case == "typ" else (1.6 if lo else 1.9)
    return {"name": "HMC8410", "G": g, "NF": nf, "IIP3": 33.0 - g}
def balun(f, case):     # TCM1-63AX+ typical table 10/2000/3000/6000 MHz; max 2.5 dB
    return float(np.interp(f, [10e6, 2e9, 3e9, 6e9], [1.70, 1.29, 1.49, 1.80])) if case == "typ" else 2.5
def spdt(f): return float(np.interp(f, [1e8, 1e9, 6e9], [0.3, 0.35, 0.6]))          # ASSUMED

def chain(f, dip, case, lna_on):
    V.SWITCH_CASE = case
    pre = [passive("limiter", 0.2), passive("diplexer HP", dip), passive("SP8T in", V.switch_loss(f)),
           passive("filter", V.filter_loss(f)), passive("SP8T out", V.switch_loss(f)), passive("SPDT LNA/bypass in", spdt(f))]
    mid = [hmc8410(f, case), passive("pad", PAD)] if lna_on else []
    post = [passive("SPDT LNA/bypass out", spdt(f)), passive("balun", balun(f, case)),
            {"name": "AD9361", "G": 60.0, "NF": float(V.ad_nf(f)), "IIP3": float(V.ad_ip3(f))}]
    V.SWITCH_CASE = "typ"
    return cascade(pre + mid + post), pre

if __name__ == "__main__":
    S = V.DIP.sim(V.DIP_L, V.DIP_C, V.F); dip = -db(S[:, 2, 0])
    rows = []
    for f, d in zip(V.F, dip):
        r = {"f_MHz": f / 1e6}
        for case in ("typ", "max"):
            on, pre = chain(f, d, case, True); off, _ = chain(f, d, case, False)
            r[case] = {"NF_LNA": round(on["NF_dB"], 1), "IIP3_LNA": round(on["IIP3_dBm"], 1),
                       "NF_bypass": round(off["NF_dB"], 1), "IIP3_bypass": round(off["IIP3_dBm"], 1),
                       "pre_LNA_loss": round(sum(-s["G"] for s in pre), 2)}
        rows.append(r)
    json.dump({"pad_dB": PAD, "rows": rows}, open(os.path.join(V.HERE, "vhf_lineup_parts.json"), "w"), indent=1)
    print(f"{'f MHz':>6} | pre-LNA loss typ/max | NF LNA typ/max | IIP3 LNA typ | NF bypass typ/max")
    for r in rows:
        t, m = r["typ"], r["max"]
        print(f"{r['f_MHz']:6.0f} | {t['pre_LNA_loss']:5.2f} / {m['pre_LNA_loss']:5.2f}      | {t['NF_LNA']:4.1f} / {m['NF_LNA']:4.1f}    | {t['IIP3_LNA']:6.1f}      | {t['NF_bypass']:4.1f} / {m['NF_bypass']:4.1f}")
