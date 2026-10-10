r"""PackPilot v0 -- Round 1 prototype (10 Oct 2026).

A deliberately small Streamlit page on top of ppt/estimates.py: pick a cell, series/parallel
layout, cooling and the ride scenario; see the baseline-vs-options table and the rule checks.
Lumped-model ESTIMATES only. Round 2 replaces the models with the fitted ECM + thermal
network + rule engine described in the research brief.

Run:  python -m streamlit run app.py --server.headless true --server.port 8501
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimates as E  # noqa: E402

st.set_page_config(page_title="PackPilot v0", layout="wide", initial_sidebar_state="collapsed")

# datasheet-class limits used by the rule engine (research PDF 06 / 09); verify before Round 2
LIMITS = {
    "Samsung INR21700-50E": {"i_cont_a": 9.8, "v_max": 4.2, "t_max_c": 60, "n_cells_note": "21700 NMC"},
    "LFP 32140 15 Ah":      {"i_cont_a": 30.0, "v_max": 3.65, "t_max_c": 60, "n_cells_note": "32140 LFP"},
}
V_HV_LINE = 60.0        # AIS-156 counts > 60 V DC as high voltage
T_DERATE = 60.0         # AIS-156 Amd 3: alarm and gradual power cut at 60 C
MIN_TEMP_SENSORS = 4    # AIS-156 Amd 3
PEAK_KW = 4.4           # iQube-class peak power target


def rules(cell: str, ns: int, npar: int, sensors: int, r: dict) -> list[tuple[str, bool, str]]:
    lim = LIMITS[cell]
    v_max_pack = ns * lim["v_max"]
    i_cell_peak = (PEAK_KW * 1000 / r["v"]) / npar
    return [
        (f"Pack max voltage {v_max_pack:.1f} V stays under the {V_HV_LINE:.0f} V DC high-voltage line",
         v_max_pack <= V_HV_LINE, "AIS-156"),
        (f"Per-cell current at {PEAK_KW} kW peak = {i_cell_peak:.1f} A vs datasheet continuous {lim['i_cont_a']} A",
         i_cell_peak <= lim["i_cont_a"], "datasheet"),
        (f"Estimated peak temperature {r['t_peak']:.0f} C stays under the {T_DERATE:.0f} C derate threshold",
         r["t_peak"] < T_DERATE, "AIS-156 Amd 3"),
        (f"{sensors} temperature sensors (minimum {MIN_TEMP_SENSORS})", sensors >= MIN_TEMP_SENSORS, "AIS-156 Amd 3"),
    ]


st.title("PackPilot v0  ·  cell-to-module design studio (prototype)")
st.caption("Lumped-model estimates from datasheet values. Every number traces to an input shown on this page.")

with st.sidebar:
    st.header("Design under test")
    cell = st.selectbox("Cell", list(E.CELLS.keys()))
    ns = st.number_input("Series (S)", 4, 20, 13)
    npar = st.number_input("Parallel (P)", 1, 20, 10)
    cooling = st.selectbox("Cooling", list(E.H.keys()))
    sensors = st.number_input("Temperature sensors", 0, 16, 4)
    st.header("Scenario")
    E.T_AMB = st.slider("Ambient (C)", 20, 50, 45)
    E.RIDE_S = st.slider("Ride duration at 1C (min)", 5, 120, 30) * 60

r = E.module(cell, ns, npar, cooling)
col1, col2, col3, col4 = st.columns(4)
col1.metric("Pack voltage", f"{r['v']:.1f} V")
col2.metric("Energy", f"{r['kwh']:.2f} kWh")
col3.metric("Peak temperature", f"~{r['t_peak']:.0f} C")
col4.metric("Module mass", f"~{r['mass']:.1f} kg")

st.subheader("Rule checks (a failure blocks the recommendation)")
for text, ok, src in rules(cell, ns, npar, sensors, r):
    st.write(("PASS  " if ok else "FAIL  ") + text + f"   [{src}]")

st.subheader("Baseline vs two options")
rows = []
base = None
for name, c, s_, p_, cool, xm, xc in E.DESIGNS:
    rr = E.module(c, s_, p_, cool, xm, xc)
    base = base or rr
    rows.append({"Design": name, "Peak T (C)": round(rr["t_peak"]), "kWh": round(rr["kwh"], 2),
                 "Mass (kg)": round(rr["mass"], 1), "Cell cost (x)": round(rr["cost"] / base["cost"], 2),
                 "Cycles": rr["life"], "Heat at 1C (W)": round(rr["q"])})
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

st.subheader("Traceability (inputs behind the numbers)")
ah, vn, m, rint, d, L, usd, life = E.CELLS[cell]
st.dataframe(pd.DataFrame([
    {"Item": "Cell capacity / nominal V / mass / DC resistance", "Value": f"{ah} Ah / {vn} V / {m*1000:.0f} g / {rint*1000:.0f} mOhm",
     "Source": "manufacturer datasheet (see research brief, cell library)"},
    {"Item": "Convective coefficient h", "Value": f"{E.H[cooling]} W/m2K ({cooling})", "Source": "textbook range, research brief 07"},
    {"Item": "Specific heat (cells)", "Value": f"{E.CP_CYL} J/kgK", "Source": "Steinhardt 2022 median, brief 06"},
    {"Item": "Module mass overhead", "Value": f"{E.OVERHEAD}x cell mass", "Source": "assumption, brief 07"},
    {"Item": "Scenario", "Value": f"{E.RIDE_S/60:.0f} min at 1C, {E.T_AMB} C ambient", "Source": "team choice"},
]), hide_index=True, use_container_width=True)
