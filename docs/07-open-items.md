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

- [ ] Diplexer: simulate with S-parameters, then standalone prototype
- [ ] Single-ended 1.8 V CMOS through the SoM connector: SI check at the chosen DATA_CLK
- [ ] TX→RX isolation on the board

## Software/gateware bring-up (can start now)

- [ ] Get a Pluto+/LibreSDR-class board (AD936x + Zynq + Ethernet)
- [ ] Build ADI HDL for it; build Linux with meta-adi / Yocto
- [ ] Measure streaming performance over Ethernet, both directions simultaneously
