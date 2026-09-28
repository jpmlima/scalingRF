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

Main risk: the HP arm must stay clean to 6 GHz while having a 60 MHz corner; shunt inductors of hundreds of nH self-resonate below 6 GHz. Needs broadband (conical) inductors or a sectioned design, simulated with real component S-parameters before layout.

---

## D9 — Bias-tee on RX: switchable, with DC block in the HF arm

A bias-tee for active antennas puts DC on the RX port, which the DC-coupled HF arm would pass straight into the FDA.

**Decision (proposed):** switchable bias-tee; when enabled, a series DC-block capacitor is switched into the HF arm. 1 kHz operation and antenna bias are mutually exclusive, which is acceptable.

---

## D10 — Filter placement in the RX VHF–6 GHz chain

Filter bank **before** the LNA. Costs ~1–2 dB of noise figure, protects the LNA from strong broadcast FM and cellular signals, which will always be present.
