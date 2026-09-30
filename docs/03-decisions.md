# 03 — Decision log

Each entry records what was decided, what else was considered and why. Prices are unit prices seen in September 2026 and will drift; they are here to explain the decision, not as a BOM.

---

## D1 — Full-duplex RFIC: AD9361

**Options considered**

| Part | Range | Notes | Price seen (1 pc) |
|---|---|---|---|
| AD9361 | 70 MHz – 6 GHz, 2×2 | Full duplex, separate TX/RX PLLs | ~$354 DigiKey; ~$72–76 LCSC |
| AD9364 | 70 MHz – 6 GHz, 1×1 | Same core, one channel | ~$270 DigiKey; ~$92 LCSC (out of stock) |
| AD9363 | 325 MHz – 3.8 GHz guaranteed | Works wider in practice (Pluto "AD9364 mode"), not guaranteed | ~$119 DigiKey/Mouser; from ~$49 LCSC |
| LMS7002M | Good to ~3.5 GHz | Would need an up/down-converter for 3.5–6 GHz | ~$151 Mouser; ~$182 LCSC (out of stock) |

**Decision:** AD9361.

Through LCSC it costs less than an LMS7002M, covers 6 GHz natively (no mixer stage) and has the most mature open ecosystem (Linux IIO driver, ADI HDL, Pluto as a reference). Buy from LCSC or authorised distribution only; broker listings far below that are counterfeit or recycled parts.

---

## D2 — Host interface: Gigabit Ethernet on a Zynq

**Options:** Zynq + Ethernet (Pluto-style) vs. FPGA + USB 3.0 FX3 (bladeRF-style).

**Decision:** Zynq + Ethernet.

- ADI's reference HDL and Linux driver for the AD9361 target Zynq directly.
- Ethernet is itself full duplex (~110 MB/s each way) and allows long cables, PoE, and running DSP on the device.
- Embedded Linux / Yocto (meta-adi) fits the project owner's background.

Cost: lower peak throughput than USB 3.0, and DDR3 — solved in D3.

---

## D3 — Processor on a SoM: Trenz TE0720 (Zynq-7020)

**Requirement:** ≥ ~110 PL I/O, bank VCCIO settable from the carrier, Gigabit PHY on module.

| SoM | Result |
|---|---|
| **Trenz TE0720** | 152 PL I/O (up to 75 LVDS pairs); banks 13/33/34/35 VCCIO independently set by carrier (1.5/1.8/2.5/3.3 V); GbE PHY on module. **Chosen.** Price not confirmed from the official shop (~€226 seen on resale). |
| MYIR MYC-C7Z020-V2 | ~$109. Public docs do not show PL I/O count or bank VCCIO options. Not verified, set aside. |
| Alinx AC7Z020 | Banks 34/35 VCCIO from carrier up to 3.3 V. Cheaper but ~100 I/O (tight) and 0.5 mm pitch connectors. Budget fallback. |

Zynq-7020 rather than 7010: the HF path adds converters and logic the Pluto's 7010 does not have.

TE0720 constraints to respect on the carrier:
- If bank 34 VCCIO is below 1.25 V the Zynq is held in reset → bank 34 carries boot-critical 3.3 V and non-critical signals only.
- Bank VCCIO must be derived from the module's 3.3 V output or gated by its Power Good.

---

## D4 — AD9361 interface: CMOS dual-port full duplex at 1.8 V

The first plan was LVDS. On Zynq-7000 HR banks, LVDS outputs require VCCO = 2.5 V, while the AD9361 digital interface runs from VDD_INTERFACE (1.8 V on the Pluto).

The ADALM-PLUTO schematic puts VDD_INTERFACE and Zynq VCCO_34/VCCO_35 on the same 1.8 V rail, which implies CMOS mode (HR banks cannot drive LVDS at 1.8 V). ADI's `axi_ad9361` IP supports both LVDS and CMOS dual-port full duplex.

**Decision:** CMOS dual-port full duplex, all AD9361 signals in one 1.8 V bank.

- Reuses the Pluto HDL, device tree and power scheme almost unchanged.
- No 2.5 V bank needed.
- CMOS caps the maximum sample rate below LVDS, but Ethernet caps it far lower anyway.
- Risk: single-ended 1.8 V signals through a board-to-board connector. Mitigation: AD9361 adjacent to the connector, series termination, length matching.

---

## D5 — Bank plan

TE0720 I/O per bank (from the module schematic): bank 35 = 48 I/O (24 pairs), bank 13 = 50 (24 pairs), bank 34 = 36 (18 pairs), bank 33 = 18 (9 pairs).

Bank 33 is too small for the HF converters, which moved to bank 13. Final plan in [04-digital.md](04-digital.md) and [../hardware/pinmap/te0720-bank-map.csv](../hardware/pinmap/te0720-bank-map.csv).

---

## D6 — HF converters: LTC2262-14 + AD9707

**ADC:** LTC2261-14 family — 14 bit, 125 Msps (LTC2262-14: 150 Msps), 73.4 dB SNR, 85 dB SFDR, full-rate CMOS / DDR CMOS / DDR LVDS outputs, CMOS output swing 1.2–1.8 V. ADI's DC1760A demo board pairs it with the LTC6409 FDA, DC–100 MHz input — essentially the HF RX front end.

Prefer **LTC2262-14 at 150 Msps**: it pushes the usable HF range to ~60 MHz so the overlap with the AD9361 does not depend on running it below its 70 MHz spec. Price to confirm (LTC2261-12 is ~$100 at DigiKey).

**DAC:** AD9707 — 14 bit, 175 MSPS, 1.7–3.6 V supply, CMOS interface, SFDR 84 dBc @ 5 MHz / 75 dBc @ 20 MHz, adjustable output common mode 0–1.2 V, pin-strap or SPI configuration. From ~$22.

The pin-compatible AD9744 is 3.3 V-only I/O, so it is **not** a drop-in for a 1.8 V bank.

Both converters use 1.8 V I/O → bank 13 at 1.8 V.

---

## D7 — HF sample rate: 150 Msps, not 153.6

153.6 MHz was first proposed because it is a multiple of typical AD9361 rates. That is unnecessary: the HF stream is independent, and coherence only needs a shared reference, not related sample rates.

With a 40 MHz reference, 150 MHz comes from an integer-N VCO (40 × 120 = 4800 MHz, ÷32), avoiding fractional-N spurs. 10 MHz reference out = 4800 ÷ 480. Divider availability to confirm in TI's TICS Pro.

---

## D8 — Front-end topology: passive diplexers, two ports

Requirement R4 (two connectors only) means the HF and VHF–6 GHz paths must share each port.

| Option | Verdict |
|---|---|
| Wideband RF switch | Switches that reach both DC/1 kHz and 6 GHz are rare or expensive |
| **Passive diplexer, crossover ~60 MHz** | LP arm is naturally DC-coupled; no control; allows HF + VHF simultaneously. **Chosen.** |

Main risk: the HP arm must stay clean to 6 GHz while having a 60 MHz corner. Simulation rev 2 (Coilcraft 0805HP manufacturer models): LP ≤ 1 dB to 49 MHz, HP ≤ 1 dB from 67 MHz, ~4 dB at the ~57 MHz crossover. The rev 1 requirement Q ≥ 60 turned out unattainable with 0805HP (Q ≈ 30–40 at 50–70 MHz); the spec was revised rather than moving to larger/air-core parts for ~1 MHz. Conical inductors are not needed. Layout must be compact (≤ 1.5 mm between HP parts, two vias per shunt part).

---

## D9 — Bias-tee on RX: switchable, with DC block in the HF arm

A bias-tee for active antennas puts DC on the RX port, which the DC-coupled HF arm would pass straight into the FDA.

**Decision (proposed):** switchable bias-tee; when enabled, a series DC-block capacitor is switched into the HF arm. 1 kHz operation and antenna bias are mutually exclusive, which is acceptable.

---

## D10 — Filter placement in the RX VHF–6 GHz chain

Filter bank **before** the LNA. Costs ~1–2 dB of noise figure, protects the LNA from strong broadcast FM and cellular signals, which will always be present.

---

## D11 — HF RX: add a switchable LNA (reverses the v0 "no LNA" choice)

Analysis (sim/hf_rx, validated against datasheet measurement): without an LNA the HF receiver NF is 16–34 dB depending on FDA gain. That is fine below ~10 MHz and in noisy locations, but at 28–49 MHz it loses 6–13 dB against quiet-rural noise and 2–6 dB even against galactic noise.

**Decision:** LNA path (1–50 MHz, NF ≤ 2 dB, ~16 dB, IIP3 ≥ +21.5 dBm) in parallel with a DC-coupled bypass; FDA fixed at AV5; 0/10/20 dB attenuator. Result: NF 7–8 dB with LNA (≤ 1 dB above galactic noise up to 49 MHz), full-scale range −19 to +17 dBm across modes.

---

## D12 — HF LNA part: LTC6433-15, with a sub-octave preselector

- LTC6433-15 A-grade: SiGe (low 1/f noise, usable at HF), 16 dB, NF 2.9–3.7 dB at 10–50 MHz, IIP3 ≈ +32 dBm. NF misses the rev 1 target (2 dB) but costs only +0.5 dB at system level; linearity exceeds it by 10 dB. Low-NF alternatives in this range typically have much lower IIP3.
- Its HD2 (−54 dBc) implies IIP2 ≈ +38 dBm; unfiltered, IM2 from two strong in-band stations lands ~44 dB above the noise floor. Required IIP2 without filtering (~+82 dBm) is not achievable by any part.
- **Decision:** LNA used only 10–49 MHz, behind a 3-band sub-octave preselector (10–17 / 17–29 / 29–49 MHz). Below 10 MHz the bypass is used (antenna-noise limited). System NF 8.5–9.2 dB, ≤ 1.3 dB above galactic noise.

---

## D13 — Preselector: elliptic sections, loss budget from noise, diplexer counted

- A plain LP+HP cascade (rev 0) lacks skirt at 2·fl; elliptic sections put transmission zeros at the critical IM2 frequencies using capacitors only.
- Loss limit per band is a curve derived from the external noise floor, not a blanket figure: B1 tolerates > 5 dB, B3 only ~2 dB at 49 MHz.
- The diplexer LP arm is part of the IM2 protection for tones above ~57 MHz (B3 would otherwise fail in 13 % of builds); its rejection must be preserved.
- Top-edge desense deviations (B2 +0.06 dB, B3 +0.15 dB worst case) accepted: smaller than the uncertainty of the ITU-R P.372 medians the limit is based on.

---

## D14 — Preselector is designed inside the chain, not in isolation

Simulating diplexer + preselector as one network showed the product-of-blocks estimate is optimistic for B3 (IIP2_eff +60.9 vs +64.5 dBm): near the diplexer crossover its LP response depends on the load, and the preselector is reactive there. B3 was re-optimised with every metric computed on the real chain (IIP2 +62.9 dBm nominal, antenna RL 9.6 → 12.4 dB). The AD9361 path is unaffected. Remaining B3 issue (sensitivity loss) is set by inductor Q.

---

## D15 — B3 preselector uses air-core inductors

0805HP Q (~45 at 30–50 MHz) left B3 at 1.70 dB sensitivity loss vs a 1.5 dB limit, failing in 82 % of builds on the real chain. Coilcraft 2222SQ/2929SQ air-core parts (Q ≈ 100–180, manufacturer transmission-line model, datasheet-checked) bring it to 1.46 dB worst case, 0 % fails. B1/B2 keep 0805HP: their noise budget is large. Cost: larger parts (up to 13 mm) and a layout requirement to control mutual coupling between coils.

---

## D16 — HF TX amplifier: LMH6702 (SOT-23) on ±5 V

Best published distortion among the candidates at our conditions (HD2/HD3 −79/−88 dBc at 20 MHz, 2 Vpp, 100 Ω), ~8 dB margin to the −65 dBc requirement at 28 MHz by pessimistic extrapolation. SOT-23 specified (SOIC is 6–7 dB worse). ±5 V rails give a ground-referenced DC-coupled output. The DAC-to-amplifier network is still open (equal loading with the optimum feedback resistor does not close at 2 mA).

---

## D17 — HF TX DAC-to-amplifier network: 5 mA, Rf ≈ 400 Ω, 0.1 % resistors

Balanced DAC loading with the LMH6702's optimum Rf (237 Ω) is impossible at any IOUTFS ≤ 5 mA; at 2 mA no Rf ≤ 750 Ω works. Among feasible designs, 5 mA / ~400 Ω gives the best estimated distortion and lowest noise; Rf = 750 Ω is excluded (inverting noise current × Rf, and loop-gain distortion estimate). Values chosen jointly in E96 (133 / 412 / 392 / 10 / DNP / 383 Ω); the four balance-critical resistors must be 0.1 %. DC offset trimmed digitally.

---

## D18 — HF TX reconstruction filter: 5 parts, designed in the chain

Designed with the diplexer LP arm in the same network. The optimiser removed two capacitors (pad-parasitic values); the diplexer provides part of the image rejection. Result: images ≤ −69.9 dBc and filter loss ≤ 0.81 dB over Monte Carlo. Side effect accepted: the TX-side diplexer HP 1 dB edge moves from 65.9 to 68.1 MHz, below the AD9361's 70 MHz specified start.

---

## D19 — VHF–6 GHz filter-bank switch: pSemi PE42582

SP8T, 9 kHz–8 GHz, 0.7–1.1 dB typical (RF1/RF8), IIP3 53–60 dBm, isolation ≥ 29 dB to 6 GHz. Highest-frequency bands on the lowest-loss ports (RF1/RF8); external −3 V on VSS_EXT to avoid the internal generator's spurs. System NF with LNA: 4.5 dB (VHF/UHF) to 6.3 dB (5.8 GHz) typical, 7.9 dB worst case at 5.8 GHz.

---

## D20 — HF LNA path: relays for the pre-LNA switching

Audit: the HF noise model counted one 0.3 dB switch before the LNA; the preselector's band-select switches were never included, and a real SOI switch has ~0.7 dB at HF. With real switches, B2 fails the desense limit in 95 % of builds and B3 in 100 %; merging the bypass into an SP4T is not enough (31 % / 97 %). Relays (~0.1 dB/pass, assumed pending part data) restore the design (0 % fails). Requirement: ≤ ~0.2 dB per pass at 29–49 MHz, two passes (SP4T in: bypass + 3 bands; SP3T out to the LNA).
