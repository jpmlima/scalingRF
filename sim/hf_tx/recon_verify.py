"""Final reconstruction filter (C1, Cz4 not fitted): AD9361 path check and Monte Carlo on the chain."""
import os, json
import numpy as np
import recon as R
from netsolve import sparams, db, loss_worst, rl_worst

j = json.load(open(os.path.join(R.HERE, "recon_design.json")))
v = np.array(j["values"]); v[0] = 1e-18; v[5] = 1e-18          # C1, Cz4 DNP
parts = tuple(j["inductors"])

if __name__ == "__main__":
    out = {"inductors": list(parts), "C1": "DNP", "Cz4": "DNP",
           "caps_pF": {"Cz2": round(v[2] * 1e12, 1), "C3": round(v[3] * 1e12, 1), "C5": round(v[6] * 1e12, 1)}}
    m, _, _ = R.metrics(R.sim(v, ("parts", parts), R.F_ALL)); out["nominal"] = {k: round(x, 2) for k, x in m.items()}
    # AD9361 path: diplexer HP arm (common <-> HP port) with the filter on the LP port vs LP port = 50 ohm
    Fh = np.logspace(np.log10(67e6), np.log10(6e9), 600)
    S = R.sim(v, ("parts", parts), Fh); ref = R.DIP.sim(R.DIP_L, R.DIP_C, Fh)
    out["HP_arm"] = {"worst_loss_with_filter_dB": round(loss_worst(S[:, 2, 1]), 2),
                     "worst_loss_diplexer_alone_dB": round(loss_worst(ref[:, 2, 0]), 2),
                     "max_change_dB": round(float(np.max(np.abs(db(S[:, 2, 1]) - db(ref[:, 2, 0])))), 2),
                     "antenna_RL_worst_dB": round(rl_worst(S[:, 1, 1]), 1)}
    # Monte Carlo: tolerances on filter AND diplexer (same distributions as the RX chain MC)
    el0, ports, nn = R.chain(v, ("parts", parts))
    import sys; sys.path.insert(0, os.path.join(R.HERE, "..", "system")); import mc_chain as MC
    rng = np.random.default_rng(9); imgs, loss, rl = [], [], []
    for _ in range(200):
        S = sparams(MC.perturb(el0, rng), ports, R.F_ALL, nn)
        mm, _, _ = R.metrics(S); imgs.append(mm["image_worst_dBc"]); loss.append(mm["filter_loss_worst_dB"]); rl.append(mm["input_RL_worst_dB"])
    out["MC_200"] = {"image_worst_dBc_max": round(max(imgs), 1), "fail_image_%": round(100 * np.mean(np.array(imgs) > -60), 1),
                     "filter_loss_worst_dB_max": round(max(loss), 2), "fail_loss_%": round(100 * np.mean(np.array(loss) > 1.0), 1),
                     "input_RL_min_dB": round(min(rl), 1)}
    json.dump(out, open(os.path.join(R.HERE, "recon_final.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
