"""UG-570 (p.15, Fig. 2) recommended phase-noise mask for the AD9361 external 40 MHz reference.
Values read from the plot by J. Lima (plot reading: ~±1 dB). check(candidate) compares an
oscillator's datasheet points against the mask (log-frequency interpolation)."""
import numpy as np

MASK = {10: -87.5, 20: -97, 50: -108, 100: -115, 200: -122, 500: -131, 1e3: -137, 2e3: -140.5,
        5e3: -143.5, 10e3: -145.5, 20e3: -147, 50e3: -148.5, 100e3: -150, 1e6: -152.75}
F = np.array(sorted(MASK)); L = np.array([MASK[f] for f in F])


def mask_at(f):
    return float(np.interp(np.log10(f), np.log10(F), L))


def check(points, name=""):
    """points: {offset_Hz: dBc/Hz} from a datasheet. Returns the worst margin (positive = better than mask)."""
    rows = [(f, v, mask_at(f), mask_at(f) - v) for f, v in sorted(points.items())]
    worst = min(r[3] for r in rows)
    print(f"{name}: worst margin {worst:+.1f} dB " + ("PASS" if worst >= 0 else "FAIL"))
    for f, v, m, d in rows:
        print(f"   {f:>9.0f} Hz  {v:7.1f}  mask {m:7.1f}  margin {d:+5.1f}")
    return worst


def lo_equiv(dbc, f_lo, f_ref=40e6):
    """In-band reference noise translated to the LO: + 20 log(f_LO / f_ref)."""
    return dbc + 20 * np.log10(f_lo / f_ref)


if __name__ == "__main__":
    assert abs(mask_at(1e3) + 137) < 1e-9 and abs(mask_at(3.1623e4) - (-147.75)) < 0.2
    print("mask self-check OK")
    check({1e3: -135, 10e3: -150, 100e3: -155}, "rev 0 provisional estimate (for the record)")
    print(f"mask at 1 kHz translated to a 6 GHz LO: {lo_equiv(mask_at(1e3), 6e9):.1f} dBc/Hz")
