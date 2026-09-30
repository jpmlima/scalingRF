# HF preselector — design report (rev 0, in progress)

Three sub-octave band-pass filters in front of the LTC6433-15 LNA (HF LNA path, 10–49 MHz): **B1 10–17, B2 17–29, B3 29–49 MHz**, 50 Ω. Purpose: stop 2nd-order intermodulation in the LNA (IIP2 ≈ +38 dBm) from strong out-of-band stations (see `sim/hf_rx` rev 2, decision D12).

**Status:** rev 0 approach (LP+HP cascade with 0805HP inductors) **fails**; spec revised from the noise analysis; elliptic redesign next.

## Metric

For every tone pair whose f1+f2 or |f1−f2| lands in the band:

IIP2_eff = IIP2_LNA + A(f1) + A(f2) − A(fp)

A = preselector loss. The product is generated after the filter (in the LNA), so it is referred back to the antenna through the in-band loss at the product frequency fp. Reported as the maximum level of two equal stations before their IM2 product exceeds the 2.4 kHz MDS (−131 dBm): P_max = (IIP2_eff + MDS)/2, and in S-units (S9 = −73 dBm).

Sanity tests (in the run log of this rev): ideal all-pass → IIP2_eff = IIP2_LNA exactly; flat 3 dB loss → +3 dB.

The critical pairs: one station **in** band plus one **above** it at ≥ 2·fl (difference product), e.g. 10.1 + 21 MHz → 10.9 MHz. 2·fl sits only 18 % above fh for a 1.7:1 band, so the filter needs a steep upper skirt there.

## Rev 0 — LP(5) + HP(5) cascade, minimum-inductor form, Coilcraft 0805HP

| Band | IL mid / worst | Rej. @ 2·fl | IIP2_eff (worst) | P_max each |
|---|---|---|---|---|
| B1 10–17 | 3.3 / 4.9 dB | 16 dB | +52.7 dBm | S9+34 |
| B2 17–29 | 2.4 / 4.1 dB | 20 dB | +56.8 dBm | S9+36 |

B3 not run: same pattern, and B3 is the band where loss matters most (below).

Why it fails: 0805HP parts of 270–820 nH have Q ≈ 20–35 at 10–30 MHz, and ten reactive elements accumulate loss; a 5+5 cascade has too little skirt at 2·fl.

## Spec revised: loss budget per band from the noise analysis

The rev 0 target "IL ≤ 1 dB in every band" was arbitrary. What matters is the system noise relative to the external noise floor (ITU-R P.372 galactic + quiet rural), which is far higher at 10 MHz than at 49 MHz.

| Band | External floor at top edge | Max loss for ≤ 1 dB desense |
|---|---|---|
| B1 | 24.8 dB above kT0 | 11.4 dB |
| B2 | 19.2 dB | 5.9 dB |
| B3 | 13.8 dB | 0.3 dB at 49 MHz; 3.0 dB for ≤ 1 dB at band centre (38 MHz); 2.1 dB for ≤ 1.5 dB at 49 MHz |

Even with **no** preselector the desense at 49 MHz is already 0.92 dB, so B3 gets a ≤ 1.5 dB-at-top criterion.

**Revised preselector spec:**

| Band | Loss (max, in band) | IIP2_eff (worst pair) |
|---|---|---|
| B1 | ≤ 6 dB | ≥ +60 dBm |
| B2 | ≤ 4 dB | ≥ +60 dBm |
| B3 | ≤ 2 dB | ≥ +60 dBm |

So B1/B2 loss is acceptable as is; the real problems are **selectivity at 2·fl** in all bands and **loss in B3**.

## Next (rev 1)

- Elliptic (Cauer) sections: transmission zeros placed at 2·fl and fh−fl (capacitors across series inductors / series-resonant shunt traps). Zeros cost capacitors (high Q, cheap), not extra inductors.
- B3: check whether 0805HP Q is enough for ≤ 2 dB; if not, derive the Q needed and look at higher-Q parts.
- Monte Carlo on the final designs; update docs.

## Reproduce

```
python3 preselector.py B1     # one band per run (~1–2 min)
```
