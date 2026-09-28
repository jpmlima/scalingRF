# 04 — Digital: SoM, banks, interfaces

## SoM

Trenz TE0720, Zynq-7020 variant. On the module: Zynq, 1 GB DDR3L, QSPI flash, eMMC, Gigabit Ethernet PHY (MDI on the board-to-board connector), USB PHY, power and sequencing.

The carrier provides: RJ45 with magnetics, VCCIO for banks 13/33/34/35, and everything else.

## Bank plan

| Bank | I/O available | VCCIO | Use | I/O used |
|---|---|---|---|---|
| 35 | 48 (24 pairs) | 1.8 V | AD9361: data, clocks, frames, SPI, control | 41 |
| 13 | 50 (24 pairs) | 1.8 V | HF ADC, HF DAC, shared SPI, 150 MHz clock in | 38 |
| 34 | 36 (18 pairs) | 3.3 V | I²C, clock PLL control, PPS, status, LEDs | ~14 |
| 33 | 18 (9 pairs) | TBD | Reserved: fast RF control (sample-synchronous band switching), expansion header | 0 |

Signal-level allocation: [../hardware/pinmap/te0720-bank-map.csv](../hardware/pinmap/te0720-bank-map.csv).

### Bank 35 — AD9361 (CMOS dual-port full duplex)

| Group | Signals | Count |
|---|---|---|
| RX data (P0) | P0_D[11:0] | 12 |
| TX data (P1) | P1_D[11:0] | 12 |
| Clocks/frames | DATA_CLK, FB_CLK, RX_FRAME, TX_FRAME | 4 |
| SPI | SPI_CLK, SPI_DI, SPI_DO, SPI_ENB | 4 |
| Control | ENABLE, TXNRX, RESETB, EN_AGC, SYNC_IN | 5 |
| Gain control | CTRL_IN[3:0] | 4 |
| **Total** | | **41 / 48** |

CTRL_OUT[7:0] is left out (debug/status only). If needed later, part of it can go to bank 33 — but bank 33 would then need 1.8 V.

DATA_CLK must land on a clock-capable pin (MRCC/SRCC).

### Bank 13 — HF converters

| Group | Signals | Count |
|---|---|---|
| ADC data | ADC_D[13:0] | 14 |
| ADC clock/status | ADC_CLKOUT, ADC_OF | 2 |
| DAC data | DAC_D[13:0] | 14 |
| DAC control | DAC_SLEEP | 1 |
| Shared SPI | SCK, SDI, SDO, CS_ADC, CS_DAC | 5 |
| HF clock copy | HFCLK_P/N (150 MHz, differential) | 2 |
| **Total** | | **38 / 50** |

ADC_CLKOUT and HFCLK_P/N must land on clock-capable pins. The FPGA does **not** generate the converter clocks; it receives them.

Full-rate CMOS chosen over DDR CMOS: simpler timing, pins are available.

### Bank 34 — slow control, 3.3 V

Boot-critical bank on the TE0720 (VCCIO34 < 1.25 V holds the Zynq in reset), so only 3.3 V non-critical signals here:

- I²C (SCL, SDA): LMK03328, RF control expanders (×2), VCTCXO tune DAC, EEPROM/temperature sensor
- ADF4002 SPI (CLK, DATA, LE) and MUXOUT (lock detect)
- PPS in, external-reference detect, LMK loss-of-lock
- RF expander interrupts (×2)
- Status LEDs

## Interfaces and IP

| Interface | IP / driver |
|---|---|
| AD9361 | ADI `axi_ad9361` (CMOS mode), `ad9361` IIO driver |
| HF ADC | Custom capture core → AXI DMA; IIO buffer driver |
| HF DAC | Custom playout core → AXI DMA; IIO buffer driver |
| Clock chip, expanders | Linux I²C drivers (standard GPIO expander drivers) |
| ADF4002 | Small SPI driver or userspace (config is static) |

## Throughput budget

Gigabit Ethernet ≈ 110 MB/s per direction. Complex 16-bit samples = 4 bytes → ~27 Msps per direction theoretical. Expect well below that with libiio over TCP on the Cortex-A9. The PL should do decimation/interpolation so the converters run at full rate while only the band of interest is streamed.
