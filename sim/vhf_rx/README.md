# VHF–6 GHz RX lineup — analysis report (rev 0)

RX port → limiter → diplexer HP arm → switch → band filter → switch → LNA (or bypass) → balun → AD9361.

**Status:** cascade analysis with the AD9361 datasheet and the real diplexer; passive losses other than the diplexer are **assumptions** until parts are chosen. Output: confirmed LNA placement, LNA gain requirement, loss budget for the filter bank.

## Data used

AD9361 at maximum RX gain (datasheet): NF 2 / 3 / 3.8 dB and IIP3 −18 / −14 / −17 dBm at 0.8 / 2.4 / 5.5 GHz; IIP2 40–45 dBm; max input +4 dBm. Diplexer HP arm from `sim/diplexer` (real models). Assumed: limiter 0.2 dB, switch 0.4 → 1.2 dB (100 MHz → 6 GHz), filter 1.0 → 1.5 dB, balun 0.8 → 1.5 dB. LNA target: NF 1.5 dB, G 18 dB, OIP3 +33 dBm.

Tool: `cascade.py` (Friis NF, cascaded IIP3), tested against a hand calculation.

## Three arrangements (`vhf_lineup.py`, LNA gain 18 dB)

| f | A: filter → LNA (D10) | B: LNA → filter | C: LNA bypass | External noise (rural / galactic) |
|---|---|---|---|---|
| 145 MHz | NF 3.7, IIP3 −33.0 | NF 2.0, −33.0 | NF 5.0, −15.0 | 7.3 / 2.3 dB |
| 435 MHz | 3.7, −33.0 | 1.9, −33.0 | 5.0, −15.0 | −5.9 / −8.7 dB |
| 2.4 GHz | 4.3, −28.5 | 2.1, −28.5 | 6.5, −10.5 | < −25 dB |
| 5.8 GHz | 6.1, −29.0 | 2.5, −29.0 | 9.8, −11.0 | < −34 dB |

(NF in dB, IIP3 in dBm, in-band.)

- **In-band IIP3 is identical in A and B**: it is set by the AD9361 (−14…−18 dBm at max gain), not by the LNA.
- **B is 1.8–3.6 dB better in NF** because the filter-bank losses come after the LNA. Its cost does not show in an in-band cascade: the LNA faces everything from 67 MHz to 6 GHz (FM broadcast, cellular, TV) unfiltered.
- **Decision: keep A (D10).** Price quantified: 1.8–3.6 dB of NF, for protection against out-of-band signals.
- **NF vs linearity**: with LNA, NF 2–6 dB and SFDR (1 MHz) 51–55 dB; in bypass, NF 5–10 dB and SFDR 62–65 dB → the bypass is a necessary strong-signal mode.
- **External noise** masks the receiver at 100–145 MHz even in bypass; **above ~400 MHz it is below kT0** and sensitivity is set by the receiver alone. That is where the LNA pays.

## LNA gain (`lna_gain.py`)

Because the AD9361 limits linearity, every dB of LNA gain costs ~1 dB of IIP3. Lowest gain within 0.5 dB of the NF asymptote:

| f | G 18 dB: NF / IIP3 | **G 12 dB: NF / IIP3** |
|---|---|---|
| 435 MHz | 3.7 dB / −33.0 dBm | 3.8 dB / −27.0 dBm |
| 2.4 GHz | 4.3 dB / −28.5 dBm | 4.5 dB / −22.5 dBm |
| 5.8 GHz | 6.1 dB / −29.0 dBm | 6.4 dB / −23.0 dBm |

→ **Net LNA gain ~12 dB** (e.g. an 18 dB part followed by a 6 dB pad): +6 dB IIP3 for ≤ 0.3 dB NF.

## Requirements derived

- **LNA**: 67 MHz–6 GHz, NF ≤ 1.5 dB, net gain ~12 dB, OIP3 ≥ +30 dBm (not dominant at 12 dB net gain), with bypass.
- **Pre-LNA loss** (switch + filter + switch) sets the NF at the top: 3.9 dB assumed at 5.8 GHz → NF 6.4 dB. Every dB saved there is ~1 dB of NF. Budget: switch ≤ 1.2 dB and filter ≤ 1.5 dB at 6 GHz.
- **Gain modes**: LNA on (sensitivity) / LNA bypass (strong signals, +10 dB SFDR), plus the AD9361 AGC.

## Next

Select switches, LNA and balun with real data; design the filter bank (in the chain, as for the preselector); then the out-of-band blocker analysis that arrangement A was chosen for.

## Reproduce

```
python3 cascade.py      # tool self-test
python3 vhf_lineup.py   # three arrangements
python3 lna_gain.py     # LNA gain trade
```
