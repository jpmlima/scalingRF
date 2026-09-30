# HF preselector — design report (rev 1)

Three sub-octave band-pass filters in front of the LTC6433-15 LNA (HF LNA path, 10–49 MHz): **B1 10–17, B2 17–29, B3 29–49 MHz**, 50 Ω. Purpose: stop 2nd-order intermodulation in the LNA (IIP2 ≈ +38 dBm) from strong out-of-band stations (sim/hf_rx rev 2, decision D12).

> **Update 2:** the noise model behind these results counted only one 0.3 dB switch before the LNA; the band-select switches were missing. With real SOI switches B2/B3 fail; relays (≤ ~0.2 dB/pass) are required — see [`sim/system/`](../system/README.md) rev 3.
>
> **Update:** B3 is superseded by a re-design done inside the real diplexer + preselector chain — see [`sim/system/`](../system/README.md). The product-of-blocks IIP2 figures below are optimistic for B3.

**Status (rev 1):** elliptic designs with real Coilcraft 0805HP models, board parasitics and Monte Carlo. All three bands meet the IIP2 target in 100 % of Monte Carlo runs (preselector + diplexer LP arm). Sensitivity loss meets its limit in B1; B2 and B3 exceed it by ≤ 0.06 / 0.15 dB at the top edge in part of the runs — accepted as documented deviations (below). **Open:** poor out-of-band match and its interaction with the diplexer.

## Metric

For every tone pair whose f1+f2 or |f1−f2| lands in the band:

IIP2_eff = IIP2_LNA + A(f1) + A(f2) − A(fp)

A = preselector loss. The product is generated after the filter (in the LNA), so it is referred back to the antenna through the in-band loss at the product frequency fp. Reported as the maximum level of two equal stations before their IM2 product exceeds the 2.4 kHz MDS (−131 dBm): P_max = (IIP2_eff + MDS)/2, and in S-units (S9 = −73 dBm).

Sanity tests (in the run log of this rev): ideal all-pass → IIP2_eff = IIP2_LNA exactly; flat 3 dB loss → +3 dB.

The critical pairs: one station **in** band plus one **above** it at ≥ 2·fl (difference product), e.g. 10.1 + 21 MHz → 10.9 MHz. 2·fl sits only 18 % above fh for a 1.7:1 band, so the filter needs a steep upper skirt there.

Rev 1 change to the metric: the diplexer LP arm (rev 2 design) sits in front of the preselector, so it is included in the attenuation of the interfering tones. Results are shown with and without it.

## Spec (derived from the noise analysis in rev 0)

| Band | Sensitivity loss (desense) vs external floor | IIP2_eff |
|---|---|---|
| B1 | ≤ 1.0 dB | ≥ +60 dBm |
| B2 | ≤ 1.0 dB | ≥ +60 dBm |
| B3 | ≤ 1.5 dB (even without a preselector it is 0.92 dB at 49 MHz) | ≥ +60 dBm |

Rev 1 turns this into a **loss budget curve per frequency** (`noise_budget.py`), used directly by the optimiser: allowed loss is large at the bottom of each band (noisy sky) and small at the top. B3: 7.9 dB at 29 MHz down to 2.1 dB at 49 MHz. The module reproduces the rev 0 hand figures (2.14 dB @ 49 MHz / 1.5 dB, 3.04 dB @ 38 MHz / 1.0 dB).

## Rev 1 — elliptic sections

Per band, 4 inductors (0805HP) + 10 C0G capacitors:

```
LP: C1 ⏚ | L2 ∥ Cz2 | C3 ⏚ | L4 ∥ Cz4 | C5 ⏚      zeros above the band (near 2·fl)
HP: C6 | L7 + Cz7 ⏚ | C8 | L9 + Cz9 ⏚ | C10         zeros below the band (near fh−fl)
```

The optimiser works directly on the worst-pair IIP2_eff (goal +62 dBm; +64 for B2 after its first Monte Carlo) and on the loss-budget curve. Inductors are then snapped to real 0805HP values (two nearest each, 16 combinations), capacitors re-optimised with the real models and snapped to E24.

### Results (100-run Monte Carlo per band)

Tolerances: L ±2 %, inductor parasitic C and loss terms ±10 %, caps ±2 % or ±0.1 pF, board parasitics ±20 %.

| | B1 10–17 | B2 17–29 | B3 29–49 |
|---|---|---|---|
| IIP2_eff nominal (presel + diplexer) | +62.0 dBm | +64.0 dBm | +64.5 dBm |
| IIP2_eff MC worst 1 % (presel + diplexer) | +60.7 dBm | +61.6 dBm | +61.2 dBm |
| IIP2_eff MC worst 1 % (presel only) | +60.2 dBm | +61.5 dBm | +58.8 dBm |
| Two stations max, each (MC worst 1 %) | S9+37.9 | S9+38.3 | S9+38.1 |
| Desense nominal / MC worst 1 % | 0.27 / 0.32 dB | 0.82 / 1.06 dB | 1.54 / 1.65 dB |
| Desense limit | 1.0 dB | 1.0 dB | 1.5 dB |
| In-band loss mid / worst | 2.61 / 5.34 dB | 1.89 / 4.94 dB | 1.16 / 2.22 dB |
| RL nominal / MC worst 1 % | 10.55 / 8.1 dB | 12.96 / 9.4 dB | 13.82 / 12.5 dB |

"Two stations max": the level each of two equal stations can have before their IM2 product exceeds the 2.4 kHz MDS, worst 1 % of builds.

### Parts

| Ref | B1 | B2 | B3 |
|---|---|---|---|
| C1 | 120 pF | 100 pF | 39 pF |
| L2 | 0805HP-331 | 0805HP-221 | 0805HP-151 |
| Cz2 | 180 pF | 68 pF | 36 pF |
| C3 | 240 pF | 150 pF | 68 pF |
| L4 | 0805HP-561 | 0805HP-221 | 0805HP-121 |
| Cz4 | 68 pF | 100 pF | 62 pF |
| C5 | 20 pF | 51 pF | 39 pF |
| C6 | 240 pF | 100 pF | 120 pF |
| L7 | 0805HP-681 | 0805HP-471 | 0805HP-271 |
| Cz7 | 820 pF | 1000 pF | 510 pF |
| C8 | 270 pF | 82 pF | 62 pF |
| L9 | 0805HP-561 | 0805HP-391 | 0805HP-471 |
| Cz9 | 2200 pF | 1000 pF | 110 pF |
| C10 | 910 pF | 200 pF | 130 pF |

All capacitors C0G. Cz7/Cz9 (820 pF – 2.2 nF) need 0603 C0G; the rest fit 0402.

Plot: `preselector_rev1.png` (S21 of the three bands; in-band loss vs budget curve).

## Accepted deviations

- **B2 desense** 1.06 dB worst case vs 1.0 dB (8 % of runs), **B3** 1.65 dB vs 1.5 dB (76 % of runs), both only at the top band edge. The limit is derived from ITU-R P.372 **median** external noise, which varies by several dB with location and time; tightening by 0.15 dB would need higher-Q inductors and buys nothing measurable. Revisit if measured antenna noise at the site is lower than the model.
- B3 IIP2 without the diplexer would fail in 13 % of runs (p1 +58.8 dBm). The diplexer is always in the path, so the combined figure is the relevant one — but it means the diplexer's LP rejection above 57 MHz is now part of the preselector's function and must be preserved in layout.

## Open issue found in rev 1 — match and diplexer interaction

Return loss is poor in places (MC worst 8.1 dB in B1) and, outside its band, each filter is almost fully reflective. In LNA mode the preselector **is the load of the diplexer's LP port**, and the diplexer was designed for 50 Ω. This may distort the crossover and even the HP arm (the AD9361 path). Must be simulated as one network (diplexer + selected preselector band) before going further; possible fixes: a small attenuator pad, absorptive (diplexer-type) band filters, or keeping the bypass path terminated.

## Engineering log

- rev 1: blanket loss limit replaced by a noise-derived budget curve; single shared module (`noise_budget.py`) used by the optimiser and the reports.
- rev 1: B2 at IIP2 goal +62 failed Monte Carlo (25 % below +60); re-optimised at +64 (0 %), trading loss at the bottom of the band where the budget is large.
- rev 1: importing `sim/hf_rx/modes.py` runs the whole script and writes files into the caller's directory. Stray files removed; `modes.py` should be refactored behind `if __name__ == "__main__"`.
- rev 0: see below.

## Rev 0 — LP(5) + HP(5) cascade, minimum-inductor form, Coilcraft 0805HP

| Band | IL mid / worst | Rej. @ 2·fl | IIP2_eff (worst) | P_max each |
|---|---|---|---|---|
| B1 10–17 | 3.3 / 4.9 dB | 16 dB | +52.7 dBm | S9+34 |
| B2 17–29 | 2.4 / 4.1 dB | 20 dB | +56.8 dBm | S9+36 |

B3 not run: same pattern, and B3 is the band where loss matters most (below).

Why it fails: 0805HP parts of 270–820 nH have Q ≈ 20–35 at 10–30 MHz, and ten reactive elements accumulate loss; a 5+5 cascade has too little skirt at 2·fl.

## Reproduce

```
python3 preselector_ell.py B1          # design one band (~1–3 min); IIP2_GOAL=64 for B2
python3 desense.py B1                  # loss and desense across the band
python3 mc.py B1 100                   # Monte Carlo
python3 preselector.py B1              # rev 0 (superseded)
```
