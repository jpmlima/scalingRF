"""AD9361 1.3 V ripple budget. No AD9361 supply-ripple sensitivity (PSMR) figure was found in
accessible ADI data, so the criterion is anchored on what ADI validated: LO phase noise measured
with the ADP1755 LDO, whose own output noise is ~23 uV rms (10 Hz-100 kHz, datasheet).
Criterion: switching ripple at the AD9361 pins far below that noise (target <= 2 uV pp)."""
import numpy as np

F_SW = 1.2e6              # ADP2164 switching frequency — ASSUMED, to verify
BUCK_RIPPLE_PP = 10e-3    # V pp at the buck output — ASSUMED worst case (ceramic output caps)
LDO_PSRR_1MHZ = 39.0      # dB, ADP1762 datasheet: 1 MHz, VIN 1.6 V, VOUT 1.3 V, 2 A (conservative for ~0.5 A)
ADP1755_NOISE = 23e-6     # V rms, ADP1755 datasheet (the part ADI validated with)
TARGET_PP = 2e-6

def lc_atten_db(f, fc, n=2):
    """Second-order LC low-pass, well damped: ~40 dB/decade above fc."""
    return 20 * n * np.log10(max(f / fc, 1.0))

for fc in (None, 300e3, 120e3):
    lc = 0.0 if fc is None else lc_atten_db(F_SW, fc)
    out = BUCK_RIPPLE_PP * 10 ** (-(lc + LDO_PSRR_1MHZ) / 20)
    label = "no post-filter" if fc is None else f"LC post-filter fc {fc/1e3:.0f} kHz ({lc:.0f} dB)"
    ok = "OK" if out <= TARGET_PP else "too high"
    print(f"{label:38s}: ripple at AD9361 {out*1e6:8.2f} uV pp  (ADP1755 own noise {ADP1755_NOISE*1e6:.0f} uV rms) -> {ok}")
