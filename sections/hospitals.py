# sections/hospitals.py
import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import geopandas as gpd
import re
import pydeck as pdk  # <-- added for the map

PAT_INCLUDE = re.compile(
    r"(hospital|emergency|urgent\s*care|walk[-\s]?in|after[-\s]?hours|"
    r"medical\s*(centre|center|clinic)|primary\s*care|doctor\b|physician\b|"
    r"community\s*health\s*(centre|center)|family\s*health\s*(team|clinic|centre|center)|health\s*hub)",
    re.I,
)
PAT_EXCLUDE = re.compile(r"(chiro|chiropractic|osteopath|osteopathy|massage|spa\b|acupuncture|naturopath)", re.I)
ALLOWLIST = ["pinpoint health", "infinity health", "appletree", "jack nathan"]


def _ensure_lat_lon(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    lat_col = next((c for c in df.columns if c.lower() in ("latitude", "lat")), None)
    lon_col = next((c for c in df.columns if c.lower() in ("longitude", "lon")), None)
    if lat_col and lon_col:
        df["Latitude"] = pd.to_numeric(df[lat_col], errors="coerce")
        df["Longitude"] = pd.to_numeric(df[lon_col], errors="coerce")
        return df
    if "geometry" in df.columns:
        gdf = df if isinstance(df, gpd.GeoDataFrame) else gpd.GeoDataFrame(df, geometry="geometry", crs=None)
        try:
            gdf = gdf.set_crs("EPSG:4326", allow_override=True) if gdf.crs is None else gdf.to_crs("EPSG:4326")
        except Exception:
            pass
        cent = gdf.geometry.centroid
        df["Latitude"], df["Longitude"] = cent.y, cent.x
        return df
    raise ValueError("Hospitals data has no Latitude/Longitude or geometry.")


def _keyword_support_mask(df: pd.DataFrame) -> pd.Series:
    name = df.get("Name", pd.Series(index=df.index, dtype=str)).astype(str).str.lower()
    addr = df.get("Address", pd.Series(index=df.index, dtype=str)).astype(str).str.lower()
    types = df.get("types", pd.Series(index=df.index, dtype=str)).astype(str).str.lower()
    blob = name + " " + addr + " " + types
    include = blob.str.contains(PAT_INCLUDE)
    exclude = blob.str_contains(PAT_EXCLUDE) if hasattr(blob, "str_contains") else blob.str.contains(PAT_EXCLUDE)
    allow = blob.apply(lambda x: any(a in x for a in ALLOWLIST))
    return (include | allow) & (~exclude)


def render(lat, lon, dguid, gdf_physio, gdf_hospitals):
    st.header("🏥 Support Facilities (Hospitals & Walk-in Clinics)")

    # --------------------------
    # Sidebar: Support controls
    # --------------------------
    with st.sidebar:
        st.markdown("### 🟩 Support controls")
        radius_km = st.slider("Search radius (km) — support", 0.5, 5.0, 2.0, 0.5, key="supp_radius")
        comparison_method = st.radio(
            "GTA comparison method (support)",
            ["Use GTA Median", "Use GTA Mean"],
            index=0,
            key="supp_gta_method",
        )
        dedup = st.checkbox("Deduplicate by Name + Address", value=True, key="supp_dedup")
        apply_filter = st.checkbox(
            "Filter to Hospitals/Walk-ins only (keyword-based)",
            value=False,
            help="Turn ON to filter by keywords. Turn OFF to show everything in hospitals GeoJSON.",
            key="supp_filter",
        )
        st.divider()

    # --------------------------
    # Prep data
    # --------------------------
    supp = _ensure_lat_lon(gdf_hospitals)
    phys = _ensure_lat_lon(gdf_physio)

    if dedup and all(c in supp.columns for c in ["Name", "Address"]):
        supp = supp.drop_duplicates(subset=["Name", "Address"]).copy()

    if apply_filter:
        supp = supp[_keyword_support_mask(supp)].copy()

    # --------------------------
    # Distance + radius filter
    # --------------------------
    input_point = (lat, lon)

    def _dist(row):
        return geodesic((row["Latitude"], row["Longitude"]), input_point).km

    supp["Distance_km"] = supp.apply(_dist, axis=1)
    phys["Distance_km"] = phys.apply(_dist, axis=1)

    nearby_support = supp[supp["Distance_km"] <= radius_km].copy()
    nearby_physios = phys[phys["Distance_km"] <= radius_km].copy()

    st.caption(
        f"Support rows: {len(gdf_hospitals)} → after dedup/filter: {len(supp)} → within {radius_km} km: {len(nearby_support)}"
        + (" | filter=ON" if apply_filter else " | filter=OFF")
    )

    # --------------------------
    # Metrics
    # --------------------------
    st.subheader("📊 Summary Metrics")
    num_support = int(len(nearby_support))
    num_physios = int(len(nearby_physios))
    ratio_sel = (num_support / num_physios) if num_physios > 0 else np.nan
    nearest_km = float(nearby_support["Distance_km"].min()) if num_support > 0 else np.nan
    support_index = float((1.0 / (1.0 + nearby_support["Distance_km"])).sum()) if num_support > 0 else 0.0

    support_counts = supp.groupby("DGUID").size().rename("Support_Count")
    physio_counts = phys.groupby("DGUID").size().rename("Physio_Count")
    aligned = pd.DataFrame({"Support_Count": support_counts}).join(physio_counts, how="outer").fillna(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        aligned["SupportPerPhysio"] = np.where(
            aligned["Physio_Count"] > 0, aligned["Support_Count"] / aligned["Physio_Count"], np.nan
        )

    agg = "median" if "median" in comparison_method.lower() else "mean"
    gta_support = getattr(aligned["Support_Count"], agg)(skipna=True)
    gta_ratio = getattr(aligned["SupportPerPhysio"], agg)(skipna=True)

    def arrow_color(d): return ("⬆️", "green") if d > 0 else ("⬇️", "red")

    c1, c2 = st.columns(2)
    c1.metric("Support Facilities Nearby", num_support)
    if pd.notnull(gta_support):
        d = num_support - gta_support
        a, col = arrow_color(d)
        c1.markdown(f"{a} <span style='color:{col}'>{d:+.1f} vs GTA {agg}</span>", unsafe_allow_html=True)

    if pd.notnull(ratio_sel) and pd.notnull(gta_ratio):
        d = ratio_sel - gta_ratio
        a, col = arrow_color(d)
        c2.markdown(
            f"""**Support / Physio Ratio**<br>
            {ratio_sel:.2f}<br>{a} <span style='color:{col}'>{d:+.2f} vs GTA {agg}</span>""",
            unsafe_allow_html=True,
        )
    else:
        c2.metric("Support / Physio Ratio", "N/A")

    c3, c4 = st.columns(2)
    c3.metric("Nearest Support Distance (km)", f"{nearest_km:.2f}" if pd.notnull(nearest_km) else "N/A")
    c4.metric("Distance-Weighted Support Index", f"{support_index:.2f}")

    # --------------------------
    # Map (same style as competitors)
    # --------------------------
    st.subheader("🗺️ Map of Support Facilities & Your Location")

    support_layer = pdk.Layer(
        "ScatterplotLayer",
        data=nearby_support.rename(columns={"Latitude": "lat", "Longitude": "lon"}),
        get_position="[lon, lat]",
        get_color="[255, 0, 0]",   # red = support facilities
        get_radius=25,
    )
    you_layer = pdk.Layer(
        "ScatterplotLayer",
        data=pd.DataFrame([{"lat": lat, "lon": lon}]),
        get_position="[lon, lat]",
        get_color="[0, 128, 255]",  # blue = your location
        get_radius=35, 
    )
    view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=13, pitch=0)
    st.pydeck_chart(
        pdk.Deck(
            map_style="mapbox://styles/mapbox/streets-v12",
            initial_view_state=view_state,
            layers=[support_layer, you_layer],
        )
    )

    # --------------------------
    # Table
    # --------------------------
    st.subheader("🏥 Hospitals & Walk-in Clinics within Radius")
    if nearby_support.empty:
        st.info("No support facilities found within the selected radius.")
    else:
        cols = [c for c in ["Name", "Address", "Distance_km"] if c in nearby_support.columns]
        st.dataframe(nearby_support.sort_values("Distance_km")[cols], use_container_width=True)
