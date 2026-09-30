# Clock — reference and phase noise (rev 2)

**Status (rev 2):** reference oscillator selected — **Microchip TX-803, 40 MHz, with EFC** — against the UG-570 mask (rev 1). Open: ordering code with EFC, and the CMOS → XTALN level/buffer design.

## Rev 2 — VCTCXO selection (`ref_mask.check`)

| Candidate | Data | Result vs UG-570 mask |
|---|---|---|
| **Microchip TX-803** (5 × 3.2 mm, EFC 0.5–2.5 V, ≤ 9 mA) | **40 MHz, CMOS, typ**: −92 / −123 / −146 / −158 / −160 dBc/Hz at 10 Hz / 100 Hz / 1 kHz / 10 kHz / 100 kHz | **PASS, worst margin +4.5 dB** (10 Hz); +8 to +12.5 dB elsewhere |
| Abracon AVTXLG-11 (3225, VC, ±0.1 ppm) | only 1 kHz −145, 10 kHz −156; carrier frequency not stated | PASS in both readings (+8 dB if at 40 MHz, +2 dB if at 20 MHz) — too few points to select |
| Abracon AST3TDA (7050, VC option) | 38.88 MHz typ / max | **FAIL**: −2.2 dB typ, −7.2 dB max |
| Taitien TP (3225, VC) | only 1 kHz −145 | not enough data |
| Microchip VT-803 (older VCTCXO) | — | **End of Life** — excluded |

**Selected: TX-803 at 40 MHz with the EFC (voltage-control) option** — the only candidate with complete 40 MHz data that passes.

Caveats:
- Phase-noise figures are **typical**; no maximum is given. The ≥ 4.5 dB margin is what covers unit-to-unit spread.
- The 40 MHz data is for the **CMOS (3.3 V) output**; clipped-sine data only exists at 20 MHz. The fan-out buffer must deliver **0.8–1.3 V pp, AC-coupled** to XTALN from a CMOS source (and suitable levels to the LMK03328 and ADF4002).
- Confirm the ordering code that includes EFC, and availability.

---

## Rev 1

## Rev 1 — ADI data

**The ADI eval board does not use an external oscillator.** AD-FMCOMMS3-EBZ BOM, Y101: **Epson TSX-3225 40.000 MHz crystal** (MFG PN OUTD-2B-0166, 3.2 × 2.5 mm) driving the **AD9361's internal DCXO**. So the datasheet LO phase-noise figures were measured in DCXO mode, not with an external reference.

**UG-570 p. 15, Fig. 2 — recommended phase-noise mask for an external 40 MHz reference** (read from the plot, ≈ ±1 dB; `ref_mask.py`):

| Offset | 10 Hz | 100 Hz | 1 kHz | 10 kHz | 100 kHz | 1 MHz |
|---|---|---|---|---|---|---|
| dBc/Hz | −87.5 | −115 | −137 | −145.5 | −150 | −152.75 |

(also 20 Hz −97, 50 Hz −108, 200 Hz −122, 500 Hz −131, 2 kHz −140.5, 5 kHz −143.5, 20 kHz −147, 50 kHz −148.5.)

`ref_mask.check()` compares any candidate's datasheet points against it. Translated to a 6 GHz LO (in-band, +43.5 dB), the mask at 1 kHz corresponds to −93.5 dBc/Hz.

**Architecture options:**
- **A (baseline): external VCTCXO meeting the mask**, feeding the AD9361 and the LMK03328 directly; hardware phase lock to an external 10 MHz (ADF4002).
- **B (fallback): crystal + AD9361 DCXO** — exactly ADI's measured configuration. The LMK03328 would take the reference from the AD9361 CLK_OUT (its quality to be checked), and external-reference lock becomes a software loop tuning the DCXO over SPI (frequency lock, not phase lock).
- A is kept for phase-coherent external locking; B if no VCTCXO at a reasonable cost meets the mask.

---

## Rev 0

## Confirmed (ADI documentation)

- AD9361 external reference on XTALN: **AC-coupled**, **0.8–1.3 V pp** (≤ 1.3 V core supply), clipped sine or square; input ≈ 10 kΩ ∥ 10 pF. The input squares the waveform internally; keep the slew rate high.
- 40 MHz reference is **doubled internally to 80 MHz** for the RF synthesisers — ADI's recommended phase-detector frequency ("as close to 80 MHz as possible"). The 40 MHz choice (docs/05-clocking.md) is confirmed.
- XTALN accepts 5–320 MHz; the phase detectors 10–80 MHz after scaling.
- Datasheet integrated LO phase noise (100 Hz–100 MHz) with a 40 MHz reference: **0.37° rms at 2.4 GHz, 0.59° rms at 5.5 GHz** (0.13° at 800 MHz with 30.72 MHz ref). These are the targets our reference must not degrade.
- UG-570: "it is extremely critical that the crystal or clock source have very low phase noise"; a recommended phase-noise mask is given at 40 MHz (plot only).
- AD9361 LO phase noise also depends on supply noise (handled in sim/power).

## ~~Provisional VCTCXO requirement~~ (superseded in rev 1 by the UG-570 mask)

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
