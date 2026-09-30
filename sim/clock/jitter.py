"""Jitter budget: TX-803 40 MHz -> LMK03328 PLL (x3.75 to 150 MHz) -> HF ADC clock.
Reference noise inside the LMK PLL bandwidth is scaled by 20log(150/40) and low-pass filtered
(2nd-order, loop BW ASSUMED 400 kHz = datasheet PSNR test condition; set in TICS Pro).
LMK03328 own jitter: 100 fs rms typ (12 kHz-20 MHz, datasheet). ADC aperture jitter from docs."""
import numpy as np

TX803 = {10: -92, 100: -123, 1e3: -146, 10e3: -158, 100e3: -160}      # 40 MHz CMOS typ (datasheet)
FLOOR = -160.0                                                        # held beyond 100 kHz (no data)
F_OUT, F_REF, LOOP_BW = 150e6, 40e6, 400e3
LMK_FS, ADC_APERTURE_FS, BUDGET_FS = 100.0, 170.0, 650.0


def ref_pn(f):
    fs = np.array(sorted(TX803)); ls = np.array([TX803[k] for k in fs])
    return np.where(f > fs[-1], FLOOR, np.interp(np.log10(f), np.log10(fs), ls))


def integrate_jitter(f, l_dbc, f_carrier):
    """rms jitter (s) from SSB phase noise L(f) [dBc/Hz]: sigma_phi^2 = 2 * integral 10^(L/10) df."""
    s = 2 * np.trapezoid(10 ** (l_dbc / 10), f)
    return np.sqrt(s) / (2 * np.pi * f_carrier)


if __name__ == "__main__":
    # analytic check: flat -150 dBc/Hz over 12 kHz-20 MHz at 150 MHz
    f = np.linspace(12e3, 20e6, 200001)
    j = integrate_jitter(f, np.full_like(f, -150.0), 150e6)
    j_exp = np.sqrt(2 * 1e-15 * (20e6 - 12e3)) / (2 * np.pi * 150e6)
    assert abs(j / j_exp - 1) < 1e-6
    print(f"integrator check OK ({j*1e15:.1f} fs for flat -150 dBc/Hz)")

    f = np.logspace(np.log10(12e3), np.log10(20e6), 20000)
    h2 = 1 / (1 + (f / LOOP_BW) ** 4)                                   # 2nd-order low-pass, |H|^2
    ref_at_out = ref_pn(f) + 20 * np.log10(F_OUT / F_REF) + 10 * np.log10(h2)
    j_ref = integrate_jitter(f, ref_at_out, F_OUT) * 1e15
    total = np.sqrt(j_ref ** 2 + LMK_FS ** 2 + ADC_APERTURE_FS ** 2)
    snr_60 = -20 * np.log10(2 * np.pi * 60e6 * total * 1e-15)
    print(f"TX-803 through LMK (12 kHz-20 MHz): {j_ref:6.1f} fs")
    print(f"LMK03328 own (datasheet typ):       {LMK_FS:6.1f} fs")
    print(f"ADC aperture:                       {ADC_APERTURE_FS:6.1f} fs")
    print(f"Total (RSS):                        {total:6.1f} fs   budget {BUDGET_FS:.0f} fs  margin {BUDGET_FS/total:.1f}x")
    print(f"Jitter-limited SNR at 60 MHz input: {snr_60:.1f} dB (ADC SNR 72.8 dB)")
    # close-in: reference noise on HF signals (reciprocal mixing), in-band of the PLL
    for fin in (7e6, 30e6, 49e6):
        l = ref_pn(np.array([1e3, 10e3])) + 20 * np.log10(F_OUT / F_REF) + 20 * np.log10(fin / F_OUT)
        print(f"  clock phase noise transferred to a {fin/1e6:4.0f} MHz signal: {l[0]:.1f} dBc/Hz @1 kHz, {l[1]:.1f} @10 kHz")
