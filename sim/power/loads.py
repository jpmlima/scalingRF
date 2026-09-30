"""scalingRF power-tree load inventory. Every load carries its source:
  DS = verified in the datasheet during this project, EST = estimate to be verified, TBD = unknown yet.
Rails are grouped by noise class: 'rf-clean' (LDO post-regulated), 'clean', 'digital'."""
import json, os

LOADS = [
    # name, rail_V, current_A (typ, design), source, noise class, note
    ("TE0720 SoM (Zynq-7020, DDR3, GbE PHY)", 3.3, 0.9, "DS: 2-3 W typ; 3 A start-up capability recommended (family TRMs)", "digital", "VIN and 3.3VIN tied (single-supply mode)"),
    ("AD9361 1.3 V (all VDDA1P3/VDDD1P3)", 1.3, 1.0, "EST: 1R1T FDD 345-490 mA (DS); 2R2T FDD higher -> budget 1.0 A", "rf-clean", "split: separate low-noise LDO for SYNTH/LO/VCO nets (UG-673)"),
    ("AD9361 VDD_INTERFACE", 1.8, 0.02, "DS: ~4-8 mA CMOS FDD", "clean", "same rail as Zynq banks 13/35 (1.8 V)"),
    ("AD9361 VDD_GPO", 3.3, 0.01, "DS: GPO outputs 10 mA max each", "digital", ""),
    ("LTC2262-14 HF ADC", 1.8, 0.083, "DS: 149 mW", "rf-clean", ""),
    ("AD9707 HF DAC (IOUTFS 5 mA)", 1.8, 0.03, "EST", "rf-clean", ""),
    ("LTC6409 HF RX FDA", 3.3, 0.055, "EST (~50 mA class)", "rf-clean", "3.3 V as in datasheet front-page circuit"),
    ("LTC6433-15 HF LNA", 5.0, 0.095, "DS: 475 mW", "rf-clean", ""),
    ("LMH6702 HF TX amp (+5 V)", 5.0, 0.0125, "EST: ~12.5 mA", "rf-clean", ""),
    ("LMH6702 HF TX amp (-5 V)", -5.0, 0.0125, "EST: ~12.5 mA", "rf-clean", ""),
    ("HMC8410 VHF LNA drain", 5.0, 0.065, "DS: 65 mA (80 max)", "rf-clean", "sequencing: after VGG1 = -2 V"),
    ("HMC8410 VGG1 (DAC-driven)", -2.0, 0.001, "DS: gate, uA", "clean", "from -3 V rail via DAC"),
    ("PE42582 x2 (VDD)", 3.3, 0.0004, "DS: 120 uA each", "clean", ""),
    ("PE42582 x2 (VSS_EXT)", -3.0, 0.0001, "DS: 16 uA each", "clean", "spur-free mode"),
    ("VCTCXO 40 MHz", 3.3, 0.01, "EST", "rf-clean", "phase-noise critical: dedicated LDO"),
    ("LMK03328 clock generator", 3.3, 0.2, "EST", "rf-clean", ""),
    ("ADF4002 + tune DAC", 3.3, 0.01, "EST", "clean", ""),
    ("Relays G6KU x4 (latching, pulsed)", 5.0, 0.0, "DS: 100 mW coil, pulse only", "digital", "H-bridge drivers; zero static current"),
    ("I2C expanders, misc logic", 3.3, 0.02, "EST", "digital", ""),
    ("VHF TX driver + TX filter-bank switches", 5.0, 0.15, "TBD (TX chain not designed)", "rf-clean", ""),
    ("VHF RX DSA + limiter", 3.3, 0.001, "TBD", "clean", ""),
]

if __name__ == "__main__":
    rails = {}
    for name, v, i, src, cls, note in LOADS:
        key = (v, cls)
        rails.setdefault(key, {"loads": [], "I": 0.0})
        rails[key]["loads"].append(name); rails[key]["I"] += i
    total_load_w = sum(abs(v) * i for _, v, i, *_ in LOADS)
    out = {"rails": [{"V": v, "class": c, "I_A": round(d["I"], 3), "P_W": round(abs(v) * d["I"], 2), "loads": d["loads"]}
                     for (v, c), d in sorted(rails.items(), key=lambda x: (-x[0][0], x[0][1]))],
           "total_load_W": round(total_load_w, 2),
           "unverified": [n for n, v, i, s, *_ in LOADS if not s.startswith("DS")]}
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "loads.json"), "w"), indent=1)
    for r in out["rails"]:
        print(f"{r['V']:+5.1f} V {r['class']:9s} {r['I_A']*1000:7.1f} mA  {r['P_W']:5.2f} W   <- {', '.join(r['loads'])}")
    print(f"\nTotal load power: {out['total_load_W']} W")
    print("Not yet datasheet-verified:", len(out["unverified"]), "loads")
