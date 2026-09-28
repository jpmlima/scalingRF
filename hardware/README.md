# Hardware

- `pinmap/` — FPGA bank and signal allocation for the TE0720 SoM (source of truth until the schematic exists).
- `kicad/` — carrier board KiCad project. Not started; see `../docs/07-open-items.md` for what must close first.

Planned sub-projects, in order:
1. `kicad/diplexer-proto/` — standalone diplexer prototype (highest-risk RF block)
2. `kicad/hf-frontend-proto/` — HF RX/TX front end with LTC2262-14 and AD9707
3. `kicad/carrier/` — full carrier board rev A
