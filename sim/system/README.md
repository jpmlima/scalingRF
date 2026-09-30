# System — diplexer + preselector as one network (rev 1)

The diplexer (rev 2) and the HF preselector (rev 1) were designed as separate 50 Ω blocks. In LNA mode the selected preselector band **is the load of the diplexer's LP port**, and out of its band it is almost fully reflective. This checks what that does, with both filters in a single nodal network (ports: antenna, LNA input, HP/AD9361 port).

**Status:** interaction quantified; B3 preselector re-optimised inside the chain. B2 passes everything; B1 and B3 miss the IIP2 target by ≤ 0.6 dB in 3 % of builds; **B3 sensitivity loss is inductor-Q-limited (1.70 dB vs 1.5 dB) — open.**

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

## Assessment

- IIP2 misses (≤ 0.6 dB, 3 % of builds) are well inside the uncertainty of the LNA's own IIP2 (+38 dBm estimated from HD2, ± several dB). Not worth chasing by simulation; accepted.
- **B3 desense** is structural: capacitor tuning cannot fix it. It is set by the 0805HP inductor Q (~40–55 at 30–50 MHz). Next step: evaluate higher-Q inductors for the 4 B3 parts only.

## Engineering log

- Node renumbering bug when merging netlists left one empty node → singular matrix. Fixed; a check now asserts every node is used.
- Same `-db(x).max()` bug as in the diplexer rev 0, this time on the HP arm loss (reported 0.08 dB instead of 0.89). Fixed by adding tested helpers `loss_worst`, `loss_best`, `rl_worst` to `netsolve.py`; all uses of the risky pattern in the repository audited — the others are correct (RL worst / minimum rejection).

## Reproduce

```
python3 dip_presel.py                     # nominal interaction, 3 bands
python3 mc_chain.py B1 100                # Monte Carlo on the chain
python3 redesign_chain.py B3 63           # re-optimise a band inside the chain
python3 mc_chain.py B3 100 chain_B3.json  # Monte Carlo of the re-design
```
