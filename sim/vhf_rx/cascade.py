"""Generic cascade: NF (Friis) and IIP3 (1/IIP3_tot = sum G_before/IIP3_i, linear mW)."""
import numpy as np


def lin(db): return 10 ** (np.asarray(db, float) / 10)
def dbv(x): return 10 * np.log10(x)


def cascade(stages):
    """stages: list of dicts {name, G (dB), NF (dB), IIP3 (dBm or None)}. Passive: NF = loss, G = -loss."""
    f_tot, g_run, inv_ip3 = 1.0, 1.0, 0.0
    for s in stages:
        f_tot += (lin(s["NF"]) - 1) / g_run
        if s.get("IIP3") is not None:
            inv_ip3 += g_run / lin(s["IIP3"])
        g_run *= lin(s["G"])
    return {"NF_dB": float(dbv(f_tot)), "G_dB": float(dbv(g_run)),
            "IIP3_dBm": float(dbv(1 / inv_ip3)) if inv_ip3 > 0 else None}


def passive(name, loss): return {"name": name, "G": -loss, "NF": loss, "IIP3": None}


if __name__ == "__main__":
    # textbook check: 3 dB loss then amp (NF 2, G 20) then second amp NF 10 -> F = 2 * (1.585 + 9/100) ...
    r = cascade([passive("pad", 3.0), {"name": "a1", "G": 20, "NF": 2.0, "IIP3": 10},
                 {"name": "a2", "G": 10, "NF": 10.0, "IIP3": 20}])
    f_expect = lin(3.0) * (lin(2.0) + (lin(10.0) - 1) / 100)
    assert abs(r["NF_dB"] - dbv(f_expect)) < 1e-9
    ip3_expect = dbv(1 / (lin(-3) / lin(10) + lin(-3 + 20) / lin(20)))
    assert abs(r["IIP3_dBm"] - ip3_expect) < 1e-9
    print("cascade tests OK:", {k: round(v, 3) for k, v in r.items()})
