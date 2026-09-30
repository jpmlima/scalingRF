# 07 — Open items

Things to verify or decide before starting schematics. Tick them off as they close.

## Parts and availability

- [ ] AD9361: confirm LCSC stock/price at order time; decide 2×2 (AD9361) vs 1×1 (AD9364) based on price
- [ ] TE0720 (Zynq-7020 variant): official price and lead time
- [ ] LMK03328: distributor stock (TI store showed out of stock); otherwise evaluate Si5332 / CDCE6214
- [ ] LTC2262-14 price vs LTC2261-14
- [ ] VCTCXO 40 MHz: pick part by phase noise; confirm tuning range and output type
- [ ] ADF4002 availability
- [ ] RF switches (SP6T/SP8T, 6 GHz), LNA, TX driver: shortlist parts

## Electrical checks

- [ ] AD9361 XTALN external clock level requirement → buffer choice
- [ ] AD9361 CMOS dual-port full duplex: confirm pin mapping and max rate in the AD9361 reference manual (UG-570)
- [ ] TE0720: per-bank pin list on the B2B connectors, identify MRCC/SRCC pins for DATA_CLK, ADC_CLKOUT, HFCLK
- [ ] TE0720: bank VCCIO sequencing on the carrier (derive from module 3.3 V / Power Good)
- [ ] LMK03328 frequency plan in TICS Pro (4800 MHz VCO, ÷32 and ÷480)
- [ ] LTC2262-14 SPI logic level at 1.8 V
- [ ] HFCLK (150 MHz differential) into a 1.8 V HR bank: confirm LVDS input without internal termination is allowed (UG471), or use LVCMOS from the LMK
- [ ] HF gain plan: antenna → ADC full scale, attenuator steps, FDA gain
- [x] Power tree rev 0 (sim/power): inventory, architecture, budget 9.1 W in (0.76 A at 12 V), sequencing/noise requirements
- [x] Power rev 1: LMK03328 (2× the estimate) and AD9361 2R2T FDD (1.02 A) verified; ADI 1.2 A buck + 300 mA LDO split adopted; 8.9 W in
- [x] Power rev 2: AD9361 supply corrected to ADI low-noise reference (ADP2164 + 2× ADP1755); VDD_GPO tied to 1.3 V; 9.7 W in
- [x] Power rev 3: AD9361 1.3 V = ADP2164 → LC post-filter (≈120 kHz) → 2× ADP1762; ripple 1.1 µV pp; 5.6 V intermediate bus; 10.2 W in
- [ ] Power: ADP2164 f_sw / sync capability vs the synchronised-switcher requirement
- [ ] Power: verify 9 remaining loads; choose remaining regulators; ripple budget for the other sensitive rails (clock, converters, LNAs); sequencer
- [ ] Ethernet throughput measured on real hardware (Pluto+/LibreSDR) with libiio

## Design risks

- [x] Diplexer: ideal + parasitic simulation, sensitivity, Monte Carlo (sim/diplexer rev 1)
- [x] Diplexer: re-simulated with Coilcraft 0805HP manufacturer models (rev 2); spec revised (LP 49 MHz / HP 67 MHz / crossover ~57 MHz, ~4 dB)
- [ ] Diplexer: capacitor manufacturer models
- [ ] Diplexer: measure HP arm 2–6 GHz on prototype (inductor models extrapolated there)
- [ ] Diplexer: layout, parasitic extraction, re-tune, openEMS on HP arm
- [ ] Single-ended 1.8 V CMOS through the SoM connector: SI check at the chosen DATA_CLK
- [ ] TX→RX isolation on the board

## Software/gateware bring-up (can start now)

- [ ] Get a Pluto+/LibreSDR-class board (AD936x + Zynq + Ethernet)
- [ ] Build ADI HDL for it; build Linux with meta-adi / Yocto
- [ ] Measure streaming performance over Ethernet, both directions simultaneously

## Simulation plan (before any purchase)

- [x] Diplexer (sim/diplexer)
- [x] HF RX lineup (sim/hf_rx rev 1): NF, full scale, gain modes; LNA path added
- [x] HF RX: LNA selected — LTC6433-15 A-grade (sim/hf_rx rev 2)
- [ ] HF RX: LTC6433-15 price/availability; add 475 mW to power budget; bias choke network per datasheet Table 1
- [x] HF RX: 3-band preselector, elliptic, 0805HP (sim/preselector rev 1): IIP2_eff ≥ +60 dBm in 100 % of Monte Carlo runs; desense deviations B2/B3 ≤ 0.15 dB accepted
- [x] HF RX: diplexer + preselector as one network (sim/system rev 1): AD9361 path not degraded; B3 re-optimised in the chain; B2 passes all; B1/B3 IIP2 ≤ 0.6 dB short in 3 % (accepted)
- [x] HF RX: B3 with air-core inductors (2222SQ/2929SQ): desense 0 % fails on the chain (sim/system rev 2)
- [ ] Layout: air-core coils in B3 — orthogonal axes / spacing / shield; EM check of mutual coupling
- [x] Refactor sim/hf_rx/modes.py so importing it has no side effects
- [ ] HF RX: switches that work from DC to 50 MHz with ≤ 0.3 dB loss (bypass, attenuator, DC block)
- [ ] HF RX: design anti-alias filter (50 Ω, deep by 90 MHz) and post-FDA RC
- [x] HF TX lineup (sim/hf_tx rev 0): level plan, image and harmonic budgets → requirements
- [x] HF TX: amplifier selected — LMH6702 SOT-23, ±5 V (sim/hf_tx rev 1)
- [x] HF TX: DAC → amplifier network (sim/hf_tx rev 2): IFS 5 mA, E96 133/412/392/10/DNP/383 Ω, 0.1 % resistors, digital DC trim
- [ ] HF TX: AD9707 SFDR vs IOUTFS (5 mA = top of range)
- [ ] Power tree: add ±5 V rails for the LMH6702
- [x] HF TX: reconstruction filter designed in the chain (sim/hf_tx rev 3): 5 parts, images ≤ −69.9 dBc, loss ≤ 0.81 dB (MC)
- [ ] HF TX: AD9707 SFDR 20–49 MHz not specified — find data or plan a measurement
- [x] VHF–6 GHz RX cascade (sim/vhf_rx rev 0): LNA after filter bank confirmed; net LNA gain ~12 dB; pre-LNA loss budget
- [x] VHF RX: filter-bank switch selected — pSemi PE42582 SP8T (sim/vhf_rx rev 1); highest bands on RF1/RF8
- [x] VHF RX: LNA HMC8410, balun TCM1-63AX+ (sim/vhf_rx rev 2); LNA bypass replaced by DSA after the LNA (D22)
- [x] VHF RX: HMC8410 bias tees — ADI eval network adopted (0402DF-591 + ATC 531Z104), measured to 10 GHz
- [ ] VHF RX: verify 0402DF-591 with Coilcraft S2P (model reconstruction from Doc 267 failed; don't force-fit)
- [ ] HMC8410 gate bias: −2…0 V DAC from −3 V rail, drain current sense, boot-time IDQ calibration, hardware-safe sequencing
- [ ] Limiter: keep LNA input ≤ +20 dBm (abs. max) with margin
- [ ] Stackup: RF sections to 6 GHz (ADI eval uses Rogers 4350) — FR-4 vs hybrid decision
- [ ] VHF RX: select the step attenuator (≥ 20 dB range, IL ≤ 2 dB at 6 GHz) and the limiter
- [ ] Power tree: +5 V / 65 mA for the HMC8410
- [x] HF preselector switch re-check (sim/system rev 3): band-select switches were missing from the noise model; with SOI switches B2/B3 fail → relays required
- [x] HF LNA path relays: Omron G6KU-2F-RF (latching DPDT), one per branch; passes with the 1 GHz max loss (B3 p99 1.49 dB)
- [ ] Relay: actual loss at 30–50 MHz (graphs/measurement); H-bridge coil drivers for single-winding latching
- [x] noise_budget.py counts every pass explicitly (PRE_LNA / POST_LNA), regression-tested
- [ ] Power tree: −3 V rail for PE42582 VSS_EXT (spur-free mode)
- [ ] VHF RX: design filter bank in the chain; out-of-band blocker analysis
- [ ] VHF–6 GHz TX cascade and filter bank: harmonic suppression per band, output power
- [ ] Clock: phase noise / jitter budget with real VCTCXO and LMK03328 data (TICS Pro)
- [ ] Digital timing: AD9361 CMOS interface and HF converter interfaces vs. Zynq HR bank timing
- [ ] Power tree: budget, sequencing, regulator noise vs. AD9361 and converter requirements
- [ ] Throughput model: Ethernet + DMA + libiio (analysis; final number needs hardware)
