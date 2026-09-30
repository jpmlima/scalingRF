# System — diplexer + preselector as one network (rev 2)

The diplexer (rev 2) and the HF preselector (rev 1) were designed as separate 50 Ω blocks. In LNA mode the selected preselector band **is the load of the diplexer's LP port**, and out of its band it is almost fully reflective. This checks what that does, with both filters in a single nodal network (ports: antenna, LNA input, HP/AD9361 port).

**Status (rev 2):** all three bands pass on the real chain. B3 now uses **air-core inductors (Coilcraft 2222SQ/2929SQ)**; B1/B2 stay on 0805HP. Remaining IIP2 misses (≤ 0.6 dB, 1–3 % of builds) accepted. New layout requirements for the air-core coils (below).

## Findings (nominal, chain vs diplexer alone)

| | B1 | B2 | B3 |
|---|---|---|---|
| HP arm (AD9361 path) worst loss 67 MHz–6 GHz | 0.66 dB (alone: 0.89) | 0.66 | 0.67 |
| Antenna RL in the AD9361 band | 12.8 dB (unchanged) | 12.8 | 12.8 |
| Antenna RL inside the HF band | 11.7 dB | 9.9 dB | 9.6 dB |
| HF path ripple from interaction | −0.14…+0.36 dB | −0.27…+0.35 | −0.25…+0.15 |
| IIP2_eff, real chain | +62.3 dBm | +65.3 | **+60.9** (product estimate was +64.5) |

- **The AD9361 path is not degraded** — it is slightly better at the 67 MHz edge.
- **The product-of-blocks estimate used in preselector rev 1 is optimistic for B3.** Worst pair 55 + 26 MHz → 29 MHz (26 MHz is CB, often strong): at 55 MHz the diplexer is in its transition band, where its LP response depends strongly on the load, and the reactive preselector costs 3.2 dB of rejection there.
- Consequence: **the preselector cannot be designed in isolation**; its out-of-band impedance is part of the performance.

## B3 re-optimised inside the chain (`redesign_chain.py`)

Same topology and inductor family; capacitors (and nearest inductor values) optimised with all metrics computed on the real chain. Design in `chain_B3.json` — **supersedes `sim/preselector/ell_B3.json`**.

| | 0805HP-151 / 101 / 271 / 471 |
|---|---|
| C1 / Cz2 / C3 / Cz4 / C5 | 24 / 27 / 82 / 75 / 39 pF |
| C6 / Cz7 / C8 / Cz9 / C10 | 120 / 510 / 62 / 100 / 180 pF |

Nominal: IIP2_eff +62.9 dBm (was +60.9), antenna RL in band 12.4 dB (was 9.6), desense 1.55 dB.

## Monte Carlo on the real chain (100 runs per band, tolerances on both filters)

| Band | IIP2_eff worst | IIP2 fails < +60 | Desense worst 1 % | Desense fails |
|---|---|---|---|---|
| B1 (preselector rev 1) | +59.7 dBm | 3 % | 0.28 dB | 0 % |
| B2 (preselector rev 1) | +63.5 dBm | 0 % | 0.89 dB | 0 % |
| B3 (chain re-design) | +59.4 dBm | 3 % | 1.70 dB | 82 % (limit 1.5) |

## Rev 2 — B3 with air-core inductors

The B3 sensitivity loss was set by 0805HP inductor Q (~45 at 30–50 MHz). Coilcraft 2222SQ/2929SQ air-core parts have Q ≈ 100–127 at 35 MHz and 140–180 at 50 MHz.

**Model** (`sim/preselector/coilcraft_sq.py`, Coilcraft Doc 836-2): ideal transmission line (Z0, electrical length) + series R2 + (R1 + C) across. Added a `TL2` element to `netsolve.py`, unit-tested (low-frequency limit equals L = Z0·τ; quarter-wave 50 Ω line matched with −90°). Checks against the datasheet: 2222SQ-161 → L 161.6 nH (160), Q@50 MHz 142 (140); 2222SQ-271 → 140 (140); 2929SQ-431 → 180 (180); 2929SQ-501 → 151 (datasheet 180 — the model is the conservative one and is used as is).

**Design** (`chain_B3_SQ.json`, supersedes `chain_B3.json`): inductors 2222SQ-131 / 2222SQ-90N / 2222SQ-271 / 2929SQ-431; caps C1 20, Cz2 33, C3 100, Cz4 82, C5 56, C6 110, Cz7 390, C8 56, Cz9 150, C10 150 pF (C0G).

| B3 on the real chain, 100-run MC | 0805HP (rev 1) | **2222/2929SQ (rev 2)** |
|---|---|---|
| Desense nominal / worst 1 % | 1.55 / 1.70 dB | **1.25 / 1.46 dB** |
| Desense fails (limit 1.5 dB) | 82 % | **0 %** |
| IIP2_eff worst | +59.4 dBm (3 % < +60) | +59.7 dBm (1 % < +60) |
| Antenna RL in band (nominal) | 12.4 dB | 11.9 dB |

**New requirements that come with air-core coils (not modelled):**
- **Mutual coupling** between coils is not in the model. Layout: alternate coil axes by 90°, spacing of at least one coil length, or a shield can per band; verify by EM simulation or measurement.
- **Size**: 2222SQ-271 is 11.7 mm long, 2929SQ-431 13.2 mm; the B3 section grows accordingly.
- **Mechanical**: air coils can be deformed by handling (inductance shifts); no rework without re-measuring.
- The Coilcraft model is valid from 10 MHz; below that (only low-frequency interfering tones) it is extrapolated — physically benign for air-core parts.

## Assessment

- IIP2 misses (≤ 0.6 dB, 3 % of builds) are well inside the uncertainty of the LNA's own IIP2 (+38 dBm estimated from HD2, ± several dB). Not worth chasing by simulation; accepted.
- **B3 desense** was structural (0805HP Q); solved in rev 2 with air-core inductors.

## Engineering log

- rev 2: first Q extraction for the SQ model (Z from S21 assuming a pure series element) gave Q = 187 vs 142 by hand: the model's shunt line capacitance breaks that assumption and a 0.36 Ω real part in a 50 Ω system is ill-conditioned. Replaced by an exact 1-port extraction, cross-checked against the closed-form model to 1e-6.
- rev 2: Monte Carlo output file names did not identify the design source, and the SQ run overwrote the 0805HP result. Names now include the source; both runs regenerated (identical numbers, fixed seed).

- Node renumbering bug when merging netlists left one empty node → singular matrix. Fixed; a check now asserts every node is used.
- Same `-db(x).max()` bug as in the diplexer rev 0, this time on the HP arm loss (reported 0.08 dB instead of 0.89). Fixed by adding tested helpers `loss_worst`, `loss_best`, `rl_worst` to `netsolve.py`; all uses of the risky pattern in the repository audited — the others are correct (RL worst / minimum rejection).

## Reproduce

```
python3 dip_presel.py                     # nominal interaction, 3 bands
python3 mc_chain.py B1 100                # Monte Carlo on the chain
python3 redesign_chain.py B3 63           # re-optimise a band inside the chain
python3 mc_chain.py B3 100 chain_B3.json  # Monte Carlo of the re-design
python3 redesign_chain.py B3 63 SQ        # B3 with air-core inductors
python3 mc_chain.py B3 100 chain_B3_SQ.json
```
