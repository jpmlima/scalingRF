"""Proposed power tree rev 0 and its input-power budget. Efficiencies are ASSUMED typical values
(bucks 88 %, charge pump 85 %); LDO loss = (Vin - Vout) * I."""
import json, os
import loads as L

BUCK_EFF, CP_EFF = 0.88, 0.85
# name, source, Vout, loads [(rail V, class)], type, Vin (for LDOs)
TREE = [
    ("BUCK_5V6", "VIN", 5.6, [], "buck", None),
    ("LDO_5V0_RF", "BUCK_5V6", 5.0, [(5.0, "rf-clean")], "ldo", 5.6),
    ("RELAYS_5V6", "BUCK_5V6", 5.6, [(5.0, "digital")], "direct", None),
    ("BUCK_3V3_DIG", "VIN", 3.3, [(3.3, "digital")], "buck", None),
    ("BUCK_3V8", "VIN", 3.8, [], "buck", None),
    ("LDO_3V3_CLK", "BUCK_3V8", 3.3, [(3.3, "rf-clean")], "ldo", 3.8),
    ("LDO_3V3_CLEAN", "BUCK_3V8", 3.3, [(3.3, "clean")], "ldo", 3.8),
    ("BUCK_1V7", "VIN", 1.7, [], "buck", None),
    ("LDO_1V3_AD9361", "BUCK_1V7", 1.3, [(1.3, "rf-clean")], "ldo", 1.7),
    ("BUCK_2V3", "VIN", 2.3, [], "buck", None),
    ("LDO_1V8_CONV", "BUCK_2V3", 1.8, [(1.8, "rf-clean")], "ldo", 2.3),
    ("LDO_1V8_IO", "BUCK_2V3", 1.8, [(1.8, "clean")], "ldo", 2.3),
    ("CP_NEG5V5", "BUCK_5V6", -5.5, [], "cp", None),
    ("LDO_NEG5V0", "CP_NEG5V5", -5.0, [(-5.0, "rf-clean")], "ldo", -5.5),
    ("LDO_NEG3V0", "CP_NEG5V5", -3.0, [(-3.0, "clean"), (-2.0, "clean")], "ldo", -5.5),
]

def rail_current(keys):
    return sum(i for _, v, i, _, c, _ in L.LOADS for k in keys if (v, c) == k)

if __name__ == "__main__":
    P = {}                                    # output power of each node, and power drawn from its source
    order = list(reversed(TREE))              # children before parents
    drawn = {n[0]: 0.0 for n in TREE}; drawn["VIN"] = 0.0
    rows = []
    for name, src, vout, keys, typ, vin in order:
        i_load = rail_current(keys)
        p_out = abs(vout) * i_load + drawn[name]              # own loads + children
        if typ == "ldo":
            i_total = i_load + (drawn[name] / abs(vout) if drawn[name] else 0)
            p_in = abs(vin) * i_total
        elif typ == "buck": p_in = p_out / BUCK_EFF
        elif typ == "cp": p_in = p_out / CP_EFF
        else: p_in = p_out
        drawn[src] += p_in
        rows.append({"node": name, "type": typ, "Vout": vout, "P_out_W": round(p_out, 3), "P_in_W": round(p_in, 3),
                     "loss_W": round(p_in - p_out, 3)})
    total_in = drawn["VIN"]; total_load = sum(abs(v) * i for _, v, i, *_ in L.LOADS)
    out = {"nodes": list(reversed(rows)), "P_loads_W": round(total_load, 2), "P_in_W": round(total_in, 2),
           "efficiency": round(total_load / total_in, 3),
           "input_current_at_12V_A": round(total_in / 12, 2)}
    json.dump(out, open(os.path.join(L.os.path.dirname(L.os.path.abspath(__file__)), "tree.json"), "w"), indent=1)
    for r in out["nodes"]:
        print(f"{r['node']:15s} {r['type']:6s} {r['Vout']:+5.1f} V  out {r['P_out_W']:5.2f} W  in {r['P_in_W']:5.2f} W  loss {r['loss_W']:5.2f} W")
    print(f"\nLoads {out['P_loads_W']} W, input {out['P_in_W']} W, efficiency {out['efficiency']*100:.0f} %, {out['input_current_at_12V_A']} A at 12 V")
