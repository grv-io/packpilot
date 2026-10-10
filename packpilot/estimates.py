r"""Round-1 model estimates for card 4 of the one-slider (baseline vs two options).

Lumped single-node transient thermal model, uniform heat generation I^2 R, convective loss
h*A*(T - T_amb). Scenario: 30-minute ride at 1C average current, 45 C ambient, module
starts at ambient. These are ESTIMATES from datasheet-class values; every input is listed
so the numbers can be traced and replaced by the Round-2 simulator.

Run:  python estimates.py   -> prints the table used in content_ps2.py
"""
import math

T_AMB = 45.0
RIDE_S = 30 * 60
CP_CYL = 912.0      # J/(kg K), cylindrical cells, Steinhardt 2022 median (research PDF 06)
OVERHEAD = 1.35     # module mass / cell mass (busbars, housing, BMS), research PDF 07 range
H = {"still air": 8.0, "forced air": 30.0, "cold plate": 150.0}  # W/(m^2 K), typical ranges, PDF 07

CELLS = {
    # name: (Ah, V_nom, mass_kg, R_dc_ohm, diameter_m, length_m, usd_per_kwh_cell, cycle_life)
    "Samsung INR21700-50E": (4.9, 3.6, 0.069, 0.030, 0.021, 0.070, 128, 500),
    # Keeppower IFR32700: 6.0 Ah, 3.2 V, ~141 g, <=10 mOhm (method not stated), 3C discharge,
    # 2000 cycles to 80 % (maker claim, condition not stated) -- research PDF 06, source [9]
    "Keeppower IFR32700 LFP 6 Ah": (6.0, 3.2, 0.141, 0.010, 0.0324, 0.0705, 81, 2000),
}


def module(cell, ns, npar, cooling, extra_mass=0.0, extra_cost_x=0.0):
    ah, vn, m, r, d, L, usd, life = CELLS[cell]
    n = ns * npar
    v_pack = ns * vn
    kwh = v_pack * ah * npar / 1000
    i_cell_1c = ah
    q = n * i_cell_1c ** 2 * r                     # W at 1C
    m_cells = n * m
    m_mod = m_cells * OVERHEAD + extra_mass
    c_heat = m_cells * CP_CYL + (m_mod - m_cells) * 500   # structure ~500 J/(kg K)
    # footprint: cells in ns x npar grid, pitch = diameter + 1 mm
    fx, fy = ns * (d + 0.001), npar * (d + 0.001)
    a_top = fx * fy
    a_side = 2 * (fx + fy) * L
    if cooling == "cold plate":
        area = a_top                                # plate on the base only
    else:
        area = 2 * a_top + a_side
    ha = H[cooling] * area
    tau = c_heat / ha
    dt = (q / ha) * (1 - math.exp(-RIDE_S / tau))
    t_peak = T_AMB + dt
    cost_cells = kwh * usd
    return dict(kwh=kwh, v=v_pack, i_cell_1c=i_cell_1c, q=q, mass=m_mod, area=area, tau=tau,
                dt=dt, t_peak=t_peak, cost=cost_cells * (1 + extra_cost_x), life=life)


DESIGNS = [
    ("A base: 13S10P NMC, still air", "Samsung INR21700-50E", 13, 10, "still air", 0.0, 0.0),
    ("B 13S10P NMC, forced air", "Samsung INR21700-50E", 13, 10, "forced air", 0.6, 0.04),
    ("C 16S8P LFP, cold plate", "Keeppower IFR32700 LFP 6 Ah", 16, 8, "cold plate", 0.8, 0.12),
]

if __name__ == "__main__":
    base = None
    print(f"Scenario: {RIDE_S/60:.0f} min at 1C, {T_AMB} C ambient, lumped model, h = {H}")
    for name, cell, ns, npar, cool, xm, xc in DESIGNS:
        r = module(cell, ns, npar, cool, xm, xc)
        if base is None:
            base = r
        print(f"{name:32s} V={r['v']:.1f}  kWh={r['kwh']:.2f}  heat@1C={r['q']:.0f} W  area={r['area']:.3f} m2  "
              f"tau={r['tau']/60:.0f} min  peakT~{r['t_peak']:.0f} C  mass~{r['mass']:.1f} kg  "
              f"cost~{r['cost']/base['cost']:.2f}x  cycles={r['life']}")
