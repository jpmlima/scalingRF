# HF RX lineup — analysis report (rev 1)

Antenna port → limiter → diplexer LP → [LNA | bypass] → attenuator → anti-alias filter → LTC6409 FDA → RC → LTC2262-14.

**Question:** how weak a signal can we hear (noise figure), where does it overload (full scale), and is sensitivity limited by the receiver or by the noise the antenna already brings in?

## Main finding — reverses an earlier decision

The architecture originally said "no LNA at HF: atmospheric noise dominates". **That is only true below ~10 MHz or in noisy (residential) locations.** Without an LNA, even at FDA gain 10 the receiver NF is 16–18 dB, which costs 6–13 dB of sensitivity at 28–49 MHz in a quiet rural location and 2–6 dB even against galactic noise, the physical floor.

**Decision:** switchable LNA path (AC-coupled, used for weak signals, ~1–50 MHz) in parallel with a DC-coupled bypass (LF/MW, strong signals). FDA gain fixed at AV5 (switching resistors in the feedback of a 10 GHz GBW amplifier is avoided); dynamic range comes from LNA on/off and a 0/10/20 dB attenuator.

## Model and validation

- ADC: LTC2262-14, 150 Msps, 2 Vpp, SNR 72.8 dB → 18.7 nV/√Hz equivalent at its input.
- FDA: LTC6409 datasheet noise equations (en 1.1 nV/√Hz, in 8.8 pA/√Hz, resistor noise, termination), wideband noise folded with a 100 MHz noise bandwidth (post-FDA RC).
- **Validation:** the LTC6409 datasheet front-page circuit (DC-coupled, RI = RF = 150 Ω, LTC2262-14 at 150 Msps, 1.8 Vpp at 70 MHz) has a measured SNR of **71.1 dB**. The model predicts **71.2–71.4 dB** (noise bandwidth 200–100 MHz). Agreement within 0.1–0.3 dB.
- External noise: ITU-R P.372 medians, Fa = c − d·log₁₀(f MHz). Galactic applied only above 10 MHz (ionospheric cutoff varies). Lossless antenna assumed.

## FDA back end (FDA + ADC, 50 Ω matched input)

| Gain | RI / RF / RT | Back-end NF | Full scale |
|---|---|---|---|
| AV1 | 150 / 150 / 66.7 Ω | 32.3 dB | +9.6 dBm |
| AV2 | 100 / 200 / 75 Ω | 26.5 dB | +3.6 dBm |
| **AV5 (chosen)** | **50 / 250 / 120 Ω** | **19.1 dB** | **−4.4 dBm** |
| AV10 | 50 / 500 / 110 Ω | 15.2 dB | −10.2 dBm |

## Gain modes at the antenna port (AV5 fixed)

| Mode | NF (0.5 → 49 MHz) | Full scale | Desense vs galactic @ 49 MHz |
|---|---|---|---|
| LNA on, att 0 | 6.6 → 7.8 dB | −19 dBm | 1.0 dB |
| Bypass, att 0 | 20.5 → 21.9 dB | −3 dBm | 9.3 dB |
| Bypass, att 10 | 30.5 → 31.9 dB | +7 dBm | 18.9 dB |
| Bypass, att 20 | 40.5 → 41.9 dB | +17 dBm | 28.8 dB |

How to read it: below ~5 MHz any mode is antenna-noise limited, so the bypass/attenuator modes can be used for large signals (MW broadcast) at no sensitivity cost. Above ~10 MHz the LNA mode is needed for weak signals; with it the receiver adds ≤ 1 dB to galactic noise up to 49 MHz.

(The quiet-rural curve falls below galactic above ~20 MHz; the real floor is their combination, so quiet-rural desense figures above 20 MHz overstate the loss.)

## Derived requirements

**LNA** (to be met by a part — not yet selected):

| Parameter | Requirement |
|---|---|
| Band | ~1–50 MHz (AC-coupled; bypass covers below) |
| NF | ≤ 2 dB |
| Gain | ~16 dB |
| IIP3 | ≥ +21.5 dBm (OIP3 ≥ +37.5 dBm) — two tones at FS−6 dB each, IMD3 ≥ 90 dBc down |

**Other assumptions to close:** switch loss 0.3 dB per pass (CMOS/SOI, must work from DC in the bypass path); anti-alias filter loss 0.3–0.9 dB (not yet designed); post-FDA RC sets ~100 MHz noise bandwidth.

## Engineering log

- rev 1: `par()` returned NaN for an infinite first argument; validation read NaN. Fixed, unit-checked, validation now 71.2–71.4 vs 71.1 dB measured.
- rev 1: "no LNA at HF" (architecture v0) contradicted by analysis; LNA path added.

## Reproduce

```
python3 lineup.py   # back-end configs, validation, NF vs external noise
python3 modes.py    # gain modes, LNA requirement
```
