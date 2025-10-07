from __future__ import annotations
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.pyplot as plt
import streamlit as st

# ---------------------- column helpers ----------------------

def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {}
    for c in df.columns:
        norm = c.strip().replace("–", "-")
        mapping[c] = norm
    return df.rename(columns=mapping)

ALIASES = {
    "DGUID": ["DGUID"],
    "geometry": ["geometry"],
    "POP2021": ["Population, 2021", "Population 2021"],
    "DENS": ["Population density per square kilometre", "Population density"],
    "GROWTH": ["Population percentage change, 2016 to 2021", "Population growth 2016-2021"],
    "MED_INC_2020": ["Median total income in 2020 among recipients ($)", "Median income 2020"],
    "AVG_INC_2020": ["Average total income in 2020 among recipients ($)", "Average income 2020"],
    "AGE_TOTAL": ["Total - Age groups of the population - 100% data"],
    "AGE_0_14": ["0 to 14 years", "0-14 years"],
    "AGE_15_64": ["15 to 64 years", "15-64 years"],
    "AGE_65_PLUS": ["65 years and over", "65+ years"],
    "AGE_85_PLUS": ["85 years and over", "85+ years"],
}

def _find_col(cols: list[str], options: list[str]) -> str | None:
    for o in options:
        if o in cols:
            return o
    return None

def _resolve_columns(df: pd.DataFrame) -> dict:
    cols = df.columns.tolist()
    resolved = {}
    for key, opts in ALIASES.items():
        resolved[key] = _find_col(cols, opts)
    return resolved

def _to_numeric(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype("object").astype(str).str.replace(r"[^0-9.\-]", "", regex=True),
        errors="coerce"
    )

# ---------------------- geospatial helper ----------------------

def _buffer_km(lat: float, lon: float, km: float) -> gpd.GeoSeries:
    point = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326")
    proj = point.to_crs(3857).buffer(km * 1000.0)
    return proj.to_crs(4326)

# ---------------------- main render ----------------------

def render(df_reduced: gpd.GeoDataFrame, dguid: str, lat: float, lon: float):
    st.header("👥 Population & Demographics")

    # --- Prep data
    gdf = gpd.GeoDataFrame(_normalize_cols(df_reduced.copy()), geometry="geometry")
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)

    cols = _resolve_columns(gdf)

    for key in ["POP2021", "DENS", "GROWTH", "MED_INC_2020", "AVG_INC_2020",
                "AGE_TOTAL", "AGE_0_14", "AGE_15_64", "AGE_65_PLUS", "AGE_85_PLUS"]:
        c = cols.get(key)
        if c and c in gdf.columns:
            gdf[c] = _to_numeric(gdf[c])

    if cols["DGUID"] is None or cols["geometry"] is None:
        st.error("Required columns (DGUID, geometry) not found.")
        return
    if dguid not in set(gdf[cols["DGUID"]].astype(str)):
        st.warning(f"DGUID {dguid} not found in data.")
        return

    row_sel = gdf[gdf[cols["DGUID"]].astype(str) == str(dguid)].iloc[0]

    # --- Radius filter
    radius_km = st.slider("Radius (km) for aggregation", min_value=0.5, max_value=10.0, value=2.0, step=0.5)
    circle = _buffer_km(lat, lon, radius_km).iloc[0]
    in_radius = gdf[gdf.geometry.intersects(circle)].copy()
    gta = gdf

    # --- Metric helpers
    def mean_safe(df, k): c = cols[k]; return df[c].replace([np.inf, -np.inf], np.nan).dropna().astype(float).mean() if c else None
    def sum_safe(df, k):  c = cols[k]; return df[c].replace([np.inf, -np.inf], np.nan).dropna().astype(float).sum() if c else None

    # --- Aggregates for selected location
    agg = {
        "Median income (2020)": mean_safe(in_radius, "MED_INC_2020"),
        "Average income (2020)": mean_safe(in_radius, "AVG_INC_2020"),
        "Population density": mean_safe(in_radius, "DENS"),
        "Population growth % (16–21)": mean_safe(in_radius, "GROWTH"),
        "Total population (2021)": sum_safe(in_radius, "POP2021"),
    }

    # --- GTA Averages (mean vs mean, except population is scaled)
    n_in = len(in_radius)
    gta_scaled_pop = mean_safe(gta, "POP2021") * n_in

    gta_avg = {
        "Median income (2020)": mean_safe(gta, "MED_INC_2020"),
        "Average income (2020)": mean_safe(gta, "AVG_INC_2020"),
        "Population density": mean_safe(gta, "DENS"),
        "Population growth % (16–21)": mean_safe(gta, "GROWTH"),
        "Total population (2021)": gta_scaled_pop,
    }

    # --- KPI Display
    st.subheader("🔑 Key Aggregates (Selected Radius vs GTA)")

    def kpi(label, val, comp):
        if val is None or comp is None or pd.isna(val) or pd.isna(comp):
            st.write(f"**{label}**: —")
            return
        delta = val - comp
        if delta > 0:
            delta_color = "normal"
        elif delta < 0:
            delta_color = "inverse"
        else:
            delta_color = "off"

        low = label.lower()
        if "income" in low:
            st.metric(label, f"${val:,.0f}", f"{delta:,.0f} vs GTA", delta_color=delta_color)
        elif "density" in low:
            st.metric(label, f"{val:,.1f} ppl/km²", f"{delta:,.1f} vs GTA", delta_color=delta_color)
        elif "growth" in low or "%" in low:
            st.metric(label, f"{val:+.1f}%", f"{delta:+.1f}% vs GTA", delta_color=delta_color)
        elif "population" in low:
            st.metric(label, f"{val:,.0f}", f"{delta:,.0f} vs GTA", delta_color=delta_color)
        else:
            st.metric(label, f"{val:,.2f}", f"{delta:,.2f} vs GTA", delta_color=delta_color)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: kpi("Median income (2020)", agg["Median income (2020)"], gta_avg["Median income (2020)"])
    with c2: kpi("Average income (2020)", agg["Average income (2020)"], gta_avg["Average income (2020)"])
    with c3: kpi("Population density", agg["Population density"], gta_avg["Population density"])
    with c4: kpi("Population growth % (16–21)", agg["Population growth % (16–21)"], gta_avg["Population growth % (16–21)"])
    with c5: kpi("Total population (2021)", agg["Total population (2021)"], gta_avg["Total population (2021)"])

    st.caption(f"Aggregates computed from {n_in} DGUID(s) intersecting a {radius_km:.1f} km circle around the selected location.")

    # [Charts are unchanged; keep existing plots below this point]
