# 01 — Requirements

## Functional

| ID | Requirement |
|---|---|
| R1 | Receive and transmit from 1 kHz to 6 GHz |
| R2 | Full duplex: TX and RX active at the same time, on independent frequencies |
| R3 | Converter resolution of at least 12 bits in every path |
| R4 | Exactly two RF connectors: one TX, one RX. All band selection is internal |
| R5 | Gigabit Ethernet host interface; the device runs its own Linux |
| R6 | Standard SDR software support (IIO/libiio, SoapySDR, GNU Radio) |

## Performance targets (initial, to be refined)

| Parameter | Target | Notes |
|---|---|---|
| Streaming bandwidth | 10–20 MHz per direction, simultaneous | GbE is ~110 MB/s each way; 4 bytes per complex sample |
| HF path usable range | 1 kHz – ~60 MHz | 150 Msps, anti-alias filter must be deep by 90 MHz |
| VHF–6 GHz path | ~65 MHz – 6 GHz | AD9361 spec starts at 70 MHz |
| TX output, VHF–6 GHz | ≥ +10 dBm where possible | AD9361 alone falls short at the top of the band |
| TX output, HF | ~0 dBm | HF power amplifier is out of scope |
| Frequency reference | 40 MHz VCTCXO, optional 10 MHz lock | |

## Constraints

- Low budget: prefer parts available through normal distribution (LCSC, DigiKey, Mouser); avoid brokers.
- Test equipment available is in the LibreVNA / tinySA class, i.e. up to ~6 GHz. Designs must be verifiable with that.
- No DDR memory layout on the carrier: the processor comes on a SoM.

## Non-goals

- Coverage above 6 GHz. A 6–10 GHz transverter could be a separate module later.
- HF power amplification.
- Same-frequency full duplex without external isolation. Isolation between TX and RX at the same frequency is mostly defined by the antennas.
- A single antenna covering 1 kHz – 6 GHz. The connectors are shared across bands; antennas are not.
