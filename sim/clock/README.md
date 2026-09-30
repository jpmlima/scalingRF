# Clock — reference and phase noise (rev 0, in progress)

**Status:** requirements collected from ADI documentation; VCTCXO **not chosen**. The ADI reference phase-noise specification exists only as a plot in UG-570 (not readable from here) and the oscillator used on ADI's eval board is only in the design-support zip. A provisional VCTCXO requirement is stated below and marked as such.

## Confirmed (ADI documentation)

- AD9361 external reference on XTALN: **AC-coupled**, **0.8–1.3 V pp** (≤ 1.3 V core supply), clipped sine or square; input ≈ 10 kΩ ∥ 10 pF. The input squares the waveform internally; keep the slew rate high.
- 40 MHz reference is **doubled internally to 80 MHz** for the RF synthesisers — ADI's recommended phase-detector frequency ("as close to 80 MHz as possible"). The 40 MHz choice (docs/05-clocking.md) is confirmed.
- XTALN accepts 5–320 MHz; the phase detectors 10–80 MHz after scaling.
- Datasheet integrated LO phase noise (100 Hz–100 MHz) with a 40 MHz reference: **0.37° rms at 2.4 GHz, 0.59° rms at 5.5 GHz** (0.13° at 800 MHz with 30.72 MHz ref). These are the targets our reference must not degrade.
- UG-570: "it is extremely critical that the crystal or clock source have very low phase noise"; a recommended phase-noise mask is given at 40 MHz (plot only).
- AD9361 LO phase noise also depends on supply noise (handled in sim/power).

## Provisional VCTCXO requirement (ESTIMATE — not an ADI figure)

Typical of good 40 MHz VCTCXOs; to be replaced by the UG-570 mask and/or the eval-board oscillator's data:

| Offset | ≤ |
|---|---|
| 1 kHz | −135 dBc/Hz |
| 10 kHz | −150 dBc/Hz |
| 100 kHz | −155 dBc/Hz |

Plus: voltage-controlled (ADF4002 disciplining), clipped-sine or CMOS output compatible with 0.8–1.3 V pp after the buffer/AC coupling, stability ±0.5 ppm or better.

Why it matters at 6 GHz: inside the AD9361 PLL bandwidth the reference noise is multiplied by 20·log(f_LO / 40 MHz) → **+43.5 dB at 6 GHz**. A −135 dBc/Hz reference at 1 kHz becomes ≈ −91.5 dBc/Hz on a 6 GHz LO.

## Stackup hint from the same eval board

AD-FMCOMMS3-EBZ is a **10-layer** board; its outer dielectrics are listed as "FR-4" but with **Dk 3.38**, which is the value of Rogers RO4003C → very likely a hybrid stackup with RF laminate on the outer layers. Together with the HMC8410 eval (Rogers 4350), input for our stackup decision.

## Open

- Get the eval-board oscillator part number from `ad-fmcomms3-ebz-designsupport.zip` (BOM) and its phase-noise data → set the VCTCXO floor to "at least as good as ADI's".
- Read the UG-570 reference phase-noise mask (plot) and replace the provisional table.
- Then: phase-noise/jitter budget through the LMK03328 to the HF converters (ADC jitter limit 0.65 ps from docs/05-clocking.md).
