# HF TX lineup — analysis report (rev 1)

AD9707 (150 MSPS) → DC-coupled differential-to-single-ended amplifier (back-terminated) → reconstruction low-pass filter (50 Ω) → switch → diplexer LP arm → TX port.

**Status (rev 1):** budgets done (rev 0); amplifier selected (**LMH6702, SOT-23, ±5 V**). Open: the DAC-to-amplifier resistor network (see below — the obvious design does not close), reconstruction filter.

## Target

- ~0 dBm at the TX port across 1 kHz – 49 MHz.
- Images and out-of-band spurs ≤ −60 dBc at the port. Harmonics ≤ −60 dBc at the port.

Level is low on purpose: the HF output feeds an external PA or a test setup; spurs must be low enough that a PA with its own low-pass filter meets any regulatory mask.

## AD9707 facts used

IOUTFS 1–5 mA (nominal 2 mA), output compliance −1…+1.25 V, SFDR 84 / 83 / 75 dBc at 5 / 10 / 20 MHz, NSD ≈ −150 dBc/Hz. **Not specified above 20 MHz** — a gap for 20–49 MHz outputs.

## Images (zero-order hold at 150 MSPS)

First image at fs − f, level f/(fs − f) relative to the tone (unit-checked: −9.54 dB at fs/4). The diplexer LP arm (rev 2, real models) already rejects part of it, so the reconstruction filter only needs the difference:

| Tone | Image | Image (ZOH) | Diplexer adds | Recon filter must add |
|---|---|---|---|---|
| 10 MHz | 140 MHz | −22.9 dBc | 46.9 dB | 0 dB |
| 30 MHz | 120 MHz | −12.0 dBc | 39.4 dB | 8.6 dB |
| 40 MHz | 110 MHz | −8.8 dBc | 35.1 dB | 16.1 dB |
| 49 MHz | 101 MHz | −6.3 dBc | 30.8 dB | **22.9 dB** |

sinc droop in band: up to 1.58 dB at 49 MHz → compensate in the PL.

## Harmonics

Tone f produces 2f, 3f. Filtering = reconstruction filter (placeholder: ideal 5th-order Chebyshev 0.1 dB, fc 50 MHz) + diplexer LP arm. Required HDn at the DAC/amplifier output so the harmonic is ≤ −60 dBc at the port:

| Tone | HD2 at | Filtering | HD2 needed | | HD3 at | HD3 needed |
|---|---|---|---|---|---|---|
| ≤ 24 MHz | ≤ 48 MHz | ≤ 0.4 dB | ≤ −60 dBc | | | |
| 26 MHz | 52 MHz | 1.4 dB | ≤ −58.6 dBc | | | |
| 28 MHz | 56 MHz | 5.2 dB | ≤ −54.8 dBc | | | |
| 30 MHz | 60 MHz | 12.4 dB | ≤ −47.6 dBc | | | |
| 36 MHz | 72 MHz | 32.9 dB | ≤ −27.1 dBc | | | |
| ≤ 15 MHz | | | | | ≤ 45 MHz | ≤ −60 dBc |
| 20 MHz | | | | | 60 MHz | ≤ −47.6 dBc |

So the hard region is **tones up to ~26 MHz: HD2/HD3 ≤ −60 dBc, not filterable**. The AD9707 covers it up to 20 MHz (≥ 75 dBc); 20–28 MHz is unspecified → risk.

## Level plan (worst case, 49 MHz)

Port 0 dBm + diplexer 0.91 dB + switch 0.3 dB + recon filter 1.0 dB (assumed) → **+2.2 dBm into the filter**, i.e. 1.63 Vpp open-circuit equivalent at a back-terminated amplifier.

| DAC load per side | DAC diff swing | Amp gain needed (sinc in PL / not) |
|---|---|---|
| 50 Ω @ 2 mA | 0.2 Vpp | 18.2 / 19.8 dB |
| 200 Ω @ 2 mA (0.4 V, within +1.25 V compliance) | 0.8 Vpp | ~6.2 / ~7.8 dB |

A higher DAC load cuts the amplifier gain by 12 dB (less noise gain, easier distortion at 49 MHz), but the datasheet SFDR is probably specified at a lower load → check.

## Requirements derived

**Amplifier** (diff → SE):
- DC-coupled, DC–49 MHz, flatness ≤ 0.5 dB (or compensated in the PL);
- gain ~8–14 dB depending on the DAC load choice;
- ≥ 1.63 Vpp open-circuit (≥ +2.2 dBm into 50 Ω, back-terminated), with ≥ 3 dB headroom;
- **HD2/HD3 ≤ −65 dBc at that level up to 28 MHz** (−60 dBc target + 5 dB so it does not dominate the DAC).

**Reconstruction filter** (50 Ω):
- passband DC–49 MHz, loss ≤ 1 dB;
- **≥ 23 dB at 101 MHz** relative to 49 MHz (the rest comes from the diplexer);
- ≥ 5th order: a 5th-order 0.1 dB Chebyshev gives 36.5 dB at 2.06·fc (hand-checked, 13.6 dB margin); 3rd order gives only ~13 dB.
- Must be verified **inside the chain** with the diplexer LP arm (same lesson as the RX preselector, D14).

## Rev 1 — amplifier selection

Requirement (rev 0): DC-coupled diff→SE, DC–49 MHz, ≥ 1.63 Vpp, HD2/HD3 ≤ −65 dBc up to 28 MHz.

| Part | Conditions (datasheet) | HD2 / HD3 | Verdict |
|---|---|---|---|
| **LMH6702 (SOT-23)** | ±5 V, G +2, 100 Ω, 2 Vpp | −100/−96 dBc @ 5 MHz; **−79/−88 dBc @ 20 MHz** | **Selected** |
| LMH6702 (SOIC) | same | −72/−82 dBc @ 20 MHz | 6–7 dB worse: package matters → SOT-23 specified |
| OPA695 | ±5 V, G +8, 100 Ω, 2 Vpp | ≈ −69/−62 dBc @ 20 MHz (read from curves) | worse |
| THS3091 | 100 Ω, 2 Vpp | −70…−74 dBc @ 10 MHz | worse |

- The datasheet stops at 20 MHz. Extrapolated to 28 MHz with a pessimistic 12 dB/octave: HD2 ≈ −73 dBc → **8 dB margin** to −65 dBc. TI also lists it as a D/A buffer and quotes "10-bit distortion through 60 MHz" into 100 Ω.
- Datasheet conditions are a non-inverting G = +2 stage; ours is a difference amplifier. Distortion is expected to be similar (same output swing and load) but is not guaranteed by the datasheet → flagged.
- **±5 V rails** are needed for a ground-referenced, truly DC-coupled output → added to the power tree. (Alternative: single supply + ≥ 10 µF output coupling, corner ~320 Hz, still reaches 1 kHz.)

### Open — the DAC-to-amplifier network does not close by hand

Target: 2.0 Vpp full scale at the amplifier (1.63 Vpp + room for the PL sinc pre-emphasis), both DAC outputs equally loaded (so even-order products and the DC common mode cancel), each output within its +1.25 V compliance.

With the LMH6702's optimum feedback resistor (237 Ω) and IOUTFS = 2 mA, the required transimpedance (1 kΩ per mA of differential current) cannot be reached with equal loading: the balance equations ask for a divider ratio above 1. Options, to be evaluated with an op-amp model in the solver (not by hand):
- raise IOUTFS towards 5 mA (check SFDR vs current);
- higher feedback resistor (CFB: lower loop gain, more distortion) — quantify;
- DAC loads large relative to a high-impedance difference stage, gain < 2.

## Engineering log

- rev 0: the first harmonic table required the amplifier to be cleaner where filtering is strongest (−123 dBc at 49 MHz) — sign error (HD − filtering at the port → requirement is target **+** filtering). Fixed; an assertion now checks the requirement never gets stricter with more filtering.
- rev 0: an early note claimed harmonics of tones above 24.5 MHz are "filtered because they land above 50 MHz". Wrong near the band edge: 2·26 MHz = 52 MHz is barely attenuated. Replaced by the computed table.

## Reproduce

```
python3 lineup.py      # images, level plan
python3 harmonics.py   # harmonic filtering and HD requirements
```
