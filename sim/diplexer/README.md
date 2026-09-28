# Diplexer — simulation report (rev 2)

Port diplexer splitting HF (DC–50 MHz) from VHF–SHF (70 MHz–6 GHz). The same design is used on the RX and TX ports.

**Status (rev 2):** design verified with **manufacturer models of the actual inductors** (Coilcraft 0805HP) plus board parasitics and Monte Carlo. Spec revised to what real parts achieve (see rev 2 below). Not yet laid out; capacitors still use a generic model.

## Rev 2 — real inductors (current design)

**Finding:** the rev 1 requirement "Q ≥ 60 at 50–70 MHz" is not met by 0805HP parts. Coilcraft's lumped model (Doc 158-27, reproduces the datasheet Q exactly: 75 @ 250 MHz for 221, 103 @ 500 MHz for 82N, 100 @ 500 MHz for 101) gives **Q ≈ 30–40 at 50–70 MHz**, rising to ~47–59 for 271.

**Method:** discrete search over available 0805HP values (72 combinations), capacitors optimised with the real inductor models and all board parasitics, snapped to E24, then 200-run Monte Carlo (L ±2 %, inductor C ±10 %, C ±2 % / ±0.1 pF, board parasitics ±20 %).

**Selected design**

| Ref | Part | | Ref | Part |
|---|---|---|---|---|
| L1 (LP series) | 0805HP-271 | | C1 (HP series) | 33 pF C0G |
| C2 (LP shunt) | 82 pF C0G | | L2 (HP shunt) | 0805HP-82N |
| L3 (LP series) | 0805HP-271 | | C3 (HP series) | 30 pF C0G |
| C4 (LP shunt) | 62 pF C0G | | L4 (HP shunt) | 0805HP-101 |
| L5 (LP series) | 0805HP-56N | | C5 (HP series) | 110 pF C0G |

**Performance (nominal / Monte Carlo worst 1 %)**

| Parameter | Result |
|---|---|
| LP 1 dB edge | 49.8 MHz / 49.2 MHz |
| HP 1 dB edge | 65.9 MHz / 66.5 MHz |
| Crossover | ~57 MHz, **~4 dB loss in each arm** |
| LP loss | 0.14 dB at DC (DCR), 0.27 dB @ 10 MHz, ~0.5 dB @ 30 MHz (skin effect) |
| HP loss 100 MHz–6 GHz | p99 0.75 dB |
| Return loss, both passbands | p1 11.3 dB |
| HP rejection @ 30 MHz / LP rejection @ 120 MHz | 37 dB / 40 dB |

**Revised spec (replaces the 50/70 MHz edges):** LP ≤ 1 dB from 1 kHz to 49 MHz; HP ≤ 1 dB from 67 MHz to 6 GHz; ~4 dB at the ~57 MHz crossover. Relative to the original target, LP loses ~1 MHz and HP gains ~3 MHz. Recovering the full 50 MHz would need higher-Q (larger or air-core) LP inductors; not worth it for 1 MHz.

**Correction:** rev 1 stated 1–3 dB extra loss around 60 MHz. With real parts the crossover point is ~4 dB.

**Open limitation — the most important one:** the Coilcraft models for 82N and 101 are only valid to 2 GHz (56N to 5 GHz). HP-arm behaviour from 2 to 6 GHz relies on **extrapolated** inductor models (shaded in the plot). This can only be closed by measurement: VNA on a prototype, or an EM model of the part. It is flagged as the first measurement to make.

Plot: `diplexer_rev2_real_parts.png`. Scripts: `real_parts.py` (search), `real_parts_mc.py` (edges + Monte Carlo), `coilcraft_0805hp.py` (model data).

---

# Rev 1 (superseded — generic parasitics)

## Specification

| Parameter | Requirement |
|---|---|
| LP (HF) insertion loss, 1 kHz–50 MHz | ≤ 1 dB |
| HP insertion loss, 70 MHz–6 GHz | ≤ 1 dB |
| Common-port return loss, both passbands | ≥ 10 dB |
| HP rejection at 30 MHz | ≥ 30 dB (keeps strong HF out of the AD9361 chain) |
| LP rejection at 120 MHz | ≥ 30 dB (keeps FM broadcast out of the HF chain) |

## Topology and values

5th-order LP (series-L first) and 5th-order HP (series-C first), paralleled at the common node. Started from Butterworth, optimised with bounds restricted to buildable ranges (L 10–680 nH, C 1–330 pF), then snapped to E12 (L) / E24 (C).

```
common ─┬─ L1 220n ─┬─ L3 220n ─┬─ L5 68n ── HF port
        │          C2 91p      C4 51p
        │           ⏚           ⏚
        └─ C1 39p ─┬─ C3 33p ─┬─ C5 82p ── VHF/SHF port
                  L2 68n     L4 82n
                   ⏚          ⏚
```

7th order was also evaluated: no meaningful gain for 4 extra parts. Rejected.

## Results

| Stage | LP IL worst | HP IL worst | RL worst | HP rej @30M | LP rej @120M | Pass |
|---|---|---|---|---|---|---|
| A. Ideal, optimised | 0.29 dB | 0.29 dB | 17.6 dB | 40.7 dB | 36.8 dB | ✔ |
| B. Snapped to E-series, ideal | 0.24 dB | 0.41 dB | 19.0 dB | 40.7 dB | 35.3 dB | ✔ |
| C. Snapped + parasitics, Q = 60 | 0.80 dB | 0.88 dB | 13.4 dB | 40.7 dB | 36.6 dB | ✔ |
| D. As C, conical L1 (Q = 20) | 1.17 dB | 1.02 dB | 15.4 dB | 40.6 dB | 36.5 dB | ✘ |
| E. Monte Carlo on C, 500 runs | p99 0.74 dB | p99 0.82 dB | p1 11.6 dB | — | — | 0 % fail |

Worst-case losses sit at the band edges (50 and 70 MHz). Away from the crossover the arms are much better: HP 0.1–0.24 dB from 100 MHz to 6 GHz, LP < 0.3 dB below 30 MHz.

**Crossover zone, 50–70 MHz:** both arms are in transition here, and extra loss of 1–3 dB is unavoidable at ~60 MHz. This is the price of sharing one connector. Coverage in that zone relies on the HF path (to ~55–60 MHz) and the AD9361 below its 70 MHz spec.

Monte Carlo tolerances: L ±2 %, C ±2 % or ±0.1 pF (whichever is larger), each parasitic ±20 %.

Plots: `diplexer_overview_n5.png`, `diplexer_hp_zoom_n5.png`, `lp_rejection_n5.png`.

## Requirements derived from the simulation

These are the outputs of this work. Parts and layout must meet them.

| Item | Requirement | Why |
|---|---|---|
| Inductor Q | **≥ 60 at 50–70 MHz** | Q = 40 fails (LP 0.97 dB, HP 1.09 dB at the edges); Q = 60 passes |
| Inductor parasitic C | **≤ 0.15 pF** → SRF ≥ 876 MHz (220 nH), ≥ 1.44 GHz (82 nH), ≥ 1.58 GHz (68 nH) | At 0.2 pF RL drops to 9.8 dB; at 0.3 pF the HP arm collapses (> 9 dB loss) |
| Via inductance per shunt element | **≤ 0.8 nH** → two vias per shunt part | 1.2 nH: HP loss 4.2 dB, RL 5.9 dB |
| Trace between HP elements | **0.5–1.5 mm** | 3 mm: HP loss 2.7 dB, RL 3.4 dB. Compact layout is mandatory |
| Conical inductor for L1 | **Not needed** | Its low Q at 50 MHz hurts more than its low parasitic C helps |

The trace-length sensitivity also means the final values must be **re-tuned after layout**, with the extracted layout parasitics.

## Model and its limits

- Linear nodal solver (`netsolve.py`), 3-port S-parameters with 50 Ω real references. Validated against an analytic 3rd-order Butterworth (−3.01 dB at fc, −18.13 dB at 2·fc, |S11|²+|S21|² = 1).
- Inductor: (Rdc + jωL + ωL/Q) ∥ Cp, constant Q. Real Q varies with frequency.
- Capacitor: C + ESL (0.35 nH) + ESR (0.15 Ω).
- Pads: 0.05 pF each. Vias: 0.4 nH. Traces: lumped π section, 50 Ω, εeff 3.3.
- **Not modelled:** manufacturer S-parameters, coupling between components, radiation, SMA launch, ground-plane return paths. These need the S2P files and ideally an EM simulation (openEMS) of the final layout.

## Engineering log

- rev 0: unbounded optimisation produced unbuildable values (8.2 pH, 0.015 pF, 3.9 nF). Fixed with bounds.
- rev 2: 0805HP models show Q ≈ 30–40 at the crossover; rev 1 Q requirement unattainable with these parts. Spec revised to measured-model reality.
- rev 2: apparent 0.5 dB flat LP loss in a plot was a misreading (that value is at 30 MHz); DC loss verified = DCR (0.141 dB model vs 0.140 dB hand calc).
- rev 0: bug in `check()` — `-db(x).max()` reported the **best** insertion loss instead of the worst. All early "pass" results on IL were wrong. Fixed (`-db(x).min()`), regression test added. After the fix, the Q = 40 design fails; the Q ≥ 60 requirement comes from this.

## Next steps

1. ~~Shortlist inductors, re-run with manufacturer models~~ → done in rev 2.
2. Replace generic capacitor model with manufacturer data (Murata/Samsung C0G, 0402).
3. Draft layout, extract parasitics, re-tune, then openEMS on the HP arm.
4. First measurement on prototype: HP arm 2–6 GHz (inductor models extrapolated there).

## Reproduce

```
python3 diplexer.py 5     # design, parasitics, Monte Carlo → results_n5.json, plots
python3 sensitivity.py    # parasitic sweeps → sensitivity_n5.json, lp_rejection_n5.png
```
Requires numpy, scipy, matplotlib.
