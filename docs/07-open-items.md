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
- [ ] Power tree: rails, sequencing, low-noise LDOs for AD9361 1.3 V analog, converter supplies
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
- [ ] HF RX: simulate diplexer + preselector as one network (preselector is reflective out of band and loads the diplexer LP port in LNA mode)
- [ ] Refactor sim/hf_rx/modes.py so importing it has no side effects
- [ ] HF RX: switches that work from DC to 50 MHz with ≤ 0.3 dB loss (bypass, attenuator, DC block)
- [ ] HF RX: design anti-alias filter (50 Ω, deep by 90 MHz) and post-FDA RC
- [ ] HF TX lineup: AD9707 → amplifier → reconstruction filter → port; images, sinc, output level
- [ ] VHF–6 GHz RX cascade: filter bank + switches + LNA + balun + AD9361 (NF, IIP3, sensitivity per band)
- [ ] VHF–6 GHz TX cascade and filter bank: harmonic suppression per band, output power
- [ ] Clock: phase noise / jitter budget with real VCTCXO and LMK03328 data (TICS Pro)
- [ ] Digital timing: AD9361 CMOS interface and HF converter interfaces vs. Zynq HR bank timing
- [ ] Power tree: budget, sequencing, regulator noise vs. AD9361 and converter requirements
- [ ] Throughput model: Ethernet + DMA + libiio (analysis; final number needs hardware)
