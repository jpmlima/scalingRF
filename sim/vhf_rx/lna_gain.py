"""LNA gain trade in arrangement A: NF and in-band IIP3 vs LNA gain (the AD9361 limits linearity,
so every dB of LNA gain costs ~1 dB of IIP3). Pick the lowest gain within 0.5 dB of the NF asymptote."""
import json, os
import numpy as np
import vhf_lineup as V
from netsolve import db

gains = [8, 10, 12, 14, 16, 18, 20, 22, 25]
S = V.DIP.sim(V.DIP_L, V.DIP_C, V.F); dip = dict(zip(V.F, -db(S[:, 2, 0])))
out = {}
for f in (435e6, 2.4e9, 5.8e9):
    rows = []
    for g in gains:
        V.LNA["G"] = float(g)
        r = V.lineup(f, "A_filter_then_LNA", dip[f])
        rows.append({"G": g, "NF": round(r["NF_dB"], 2), "IIP3": round(r["IIP3_dBm"], 1)})
    nf_inf = rows[-1]["NF"]
    pick = next(r for r in rows if r["NF"] <= nf_inf + 0.5)
    out[f"{f/1e6:.0f} MHz"] = {"rows": rows, "pick_within_0.5dB_of_asymptote": pick}
V.LNA["G"] = 18.0
json.dump(out, open(os.path.join(V.HERE, "lna_gain_results.json"), "w"), indent=1)
for k, v in out.items():
    print(k, " ".join(f"G{r['G']}:NF{r['NF']}/IP3{r['IIP3']}" for r in v["rows"]))
    print("   pick:", v["pick_within_0.5dB_of_asymptote"])
