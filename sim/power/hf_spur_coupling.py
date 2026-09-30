"""How much magnetic coupling from a buck inductor into the HF RX input is tolerable.
Coupled spur at the LNA input must stay >= 6 dB below the 2.4 kHz MDS (LNA mode, sim/hf_rx).
V_coupled = 2*pi*f*M*I_ripple  ->  M_max. Harmonics: triangular inductor current, amplitude ~ 1/n^2."""
import numpy as np

MDS_DBM = -131.0 - 6.0                          # dBm, 2.4 kHz, LNA mode, 6 dB margin
V_MAX = np.sqrt(50 * 10 ** (MDS_DBM / 10) / 1000)  # V rms across 50 ohm
F_SW = 1.25e6
I_PP = 0.3                                       # A pp inductor ripple (~30 % of a 1 A buck) — ASSUMED

print(f"Allowed spur at HF LNA input: {MDS_DBM:.0f} dBm = {V_MAX*1e9:.1f} nV rms")
for n in (1, 3, 5, 9, 21, 39):                   # odd harmonics of a triangle; 39 * 1.25 MHz ~ 49 MHz
    i_rms = (I_PP / 2) * (8 / np.pi ** 2) / n ** 2 / np.sqrt(2)
    f = n * F_SW
    m_max = V_MAX / (2 * np.pi * f * i_rms)
    print(f"  harmonic {n:2d} ({f/1e6:5.2f} MHz): ripple current {i_rms*1e3:7.3f} mA rms -> M_max {m_max*1e15:8.2f} fH")
# reference scale: two coaxial 5 mm loops 20 mm apart, M ~ mu0*pi*a^2*b^2/(2*d^3)
mu0 = 4e-7 * np.pi; a = b = 2.5e-3
for d in (20e-3, 50e-3):
    m = mu0 * np.pi * a ** 2 * b ** 2 / (2 * d ** 3)
    print(f"reference: two 5 mm loops, coaxial, {d*1e3:.0f} mm apart, unshielded: M ~ {m*1e15:.0f} fH")
