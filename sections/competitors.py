# sections/competitors.py
import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import pydeck as pdk
import matplotlib.pyplot as plt


def render(gdf_physio, dguid, lat, lon, df_reduced):
    st.header("🏥 Nearby Competitors (Physio Clinics)")

    # ---------------------------------------------------------
    # Inline Filters (replacing sidebar)
    # ---------------------------------------------------------
    with st.container():
        st.subheader("🔍 Filter Nearby Clinics")
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1.2])

        with col1:
            radius_km = st.slider(
                "Search radius (km)",
                min_value=0.5,
                max_value=5.0,
                step=0.5,
                value=2.0,
                key="comp_radius_km_main",
            )
        with col2:
            min_rating = st.slider(
                "Minimum rating",
                min_value=1.0,
                max_value=5.0,
                value=3.5,
                step=0.1,
                key="comp_min_rating_main",
            )
        with col3:
            gta_method = st.radio(
                "GTA comparison method",
                ["Use GTA Median", "Use GTA Mean"],
                index=0,
                key="comp_gta_method_main",
                horizontal=True,
            )
        with col4:
            dedup = st.checkbox(
                "Deduplicate by Name + Address",
                value=True,
                key="comp_dedup_main",
            )

    st.markdown("---")

    # ---------------------------------------------------------
    # Filter clinics within radius
    # ---------------------------------------------------------
    input_point = (lat, lon)

    def _dist_km(row):
        return geodesic(input_point, (row["Latitude"], row["Longitude"])).km

    gdf_physio = gdf_physio.copy()
    gdf_physio["Distance_km"] = gdf_physio.apply(_dist_km, axis=1)

    nearby = gdf_physio[gdf_physio["Distance_km"] <= radius_km].copy()
    if dedup:
        nearby = nearby.drop_duplicates(subset=["Name", "Address"])

    combined = nearby.query("Rating >= @min_rating").copy()

    # ---------------------------------------------------------
    # Data table
    # ---------------------------------------------------------
    st.subheader("📍 Filtered Nearby Clinics")
    if combined.empty:
        st.info("No clinics match your criteria.")
    else:
        st.dataframe(
            combined[["Name", "Address", "Rating", "User Ratings Total", "Distance_km"]],
            use_container_width=True,
        )

    # ---------------------------------------------------------
    # Map
    # ---------------------------------------------------------
    st.subheader("🗺️ Map of Clinics & Your Location")
    if not combined.empty:
        clinics_layer = pdk.Layer(
            "ScatterplotLayer",
            data=combined.rename(columns={"Latitude": "lat", "Longitude": "lon"}),
            get_position="[lon, lat]",
            get_color="[255, 0, 0]",
            get_radius=25,
        )
        input_layer = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame([{"lat": lat, "lon": lon}]),
            get_position="[lon, lat]",
            get_color="[0, 128, 255]",
            get_radius=35,
        )
        view_state = pdk.ViewState(latitude=lat, longitude=lon, zoom=13, pitch=0)
        st.pydeck_chart(
            pdk.Deck(
                map_style="mapbox://styles/mapbox/streets-v12",
                initial_view_state=view_state,
                layers=[clinics_layer, input_layer],
            )
        )
    else:
        st.info("No clinics found within this radius.")

    # ---------------------------------------------------------
    # Metrics for selected area
    # ---------------------------------------------------------
    st.subheader("📊 Competitiveness Metrics")

    dguids_in_radius = combined["DGUID"].unique()
    dguid_stats = df_reduced[df_reduced["DGUID"].isin(dguids_in_radius)].copy()

    total_population = pd.to_numeric(
        dguid_stats["Population, 2021"], errors="coerce"
    ).sum(skipna=True)

    num_clinics = len(combined)
    pop_per_clinic_sel = (total_population / num_clinics) if num_clinics > 0 else np.nan
    clinics_per_1000_sel = (
        (num_clinics / total_population) * 1000 if total_population > 0 else np.nan
    )
    avg_rating_sel = combined["Rating"].mean() if not combined.empty else np.nan
    total_reviews_sel = combined["User Ratings Total"].sum() if not combined.empty else 0
    reviews_per_1000_sel = (
        (total_reviews_sel / total_population) * 1000 if total_population > 0 else np.nan
    )

    # ---------------------------------------------------------
    # Build GTA baselines safely
    # ---------------------------------------------------------
    df_tmp = df_reduced.copy()
    df_tmp["Population, 2021"] = pd.to_numeric(
        df_tmp["Population, 2021"], errors="coerce"
    )

    clinic_counts = gdf_physio.groupby("DGUID").size().reset_index(name="Num_Clinics")
    df_tmp = df_tmp.merge(clinic_counts, on="DGUID", how="left")
    df_tmp["Num_Clinics"] = df_tmp["Num_Clinics"].fillna(0)

    agg_reviews = (
        gdf_physio.groupby("DGUID")
        .agg(
            **{
                "Total_Reviews": ("User Ratings Total", "sum"),
                "Average_Rating": ("Rating", "mean"),
            }
        )
        .reset_index()
    )
    df_tmp = df_tmp.merge(agg_reviews, on="DGUID", how="left")
    df_tmp["Total_Reviews"] = df_tmp["Total_Reviews"].fillna(0)
    df_tmp["Average_Rating"] = df_tmp["Average_Rating"].fillna(0)

    pop = df_tmp["Population, 2021"].astype(float)

    with np.errstate(divide="ignore", invalid="ignore"):
        df_tmp["PopPerClinic"] = np.where(
            df_tmp["Num_Clinics"] > 0, pop / df_tmp["Num_Clinics"], np.nan
        )
        df_tmp["ClinicsPer1000"] = np.where(
            pop > 0, (df_tmp["Num_Clinics"] / pop) * 1000, np.nan
        )
        df_tmp["ReviewsPer1000"] = np.where(
            pop > 0, (df_tmp["Total_Reviews"] / pop) * 1000, np.nan
        )

    for col in ["PopPerClinic", "ClinicsPer1000", "ReviewsPer1000", "Average_Rating"]:
        df_tmp[col] = pd.to_numeric(df_tmp[col], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )

    if "median" in gta_method.lower():
        gta_pop_per_clinic = df_tmp["PopPerClinic"].median(skipna=True)
        gta_clinics_per_1000 = df_tmp["ClinicsPer1000"].median(skipna=True)
        gta_reviews_per_1000 = df_tmp["ReviewsPer1000"].median(skipna=True)
    else:
        gta_pop_per_clinic = df_tmp["PopPerClinic"].mean(skipna=True)
        gta_clinics_per_1000 = df_tmp["ClinicsPer1000"].mean(skipna=True)
        gta_reviews_per_1000 = df_tmp["ReviewsPer1000"].mean(skipna=True)

    gta_avg_rating = df_tmp.loc[
        df_tmp["Average_Rating"] > 0, "Average_Rating"
    ].mean(skipna=True)

    def arrow_color(diff: float):
        arrow = "⬆️" if diff > 0 else "⬇️"
        color = "green" if diff > 0 else "red"
        return arrow, color

    c1, c2 = st.columns(2)
    if pd.notnull(pop_per_clinic_sel) and pd.notnull(gta_pop_per_clinic):
        diff = pop_per_clinic_sel - gta_pop_per_clinic
        arrow, color = arrow_color(diff)
        c1.markdown(
            f"""**Population per Clinic**<br>
            {pop_per_clinic_sel:,.1f}<br>
            {arrow} <span style='color:{color}'>{diff:+,.1f} vs GTA</span>""",
            unsafe_allow_html=True,
        )
    else:
        c1.metric("Population per Clinic", "N/A")

    if pd.notnull(clinics_per_1000_sel) and pd.notnull(gta_clinics_per_1000):
        diff = clinics_per_1000_sel - gta_clinics_per_1000
        arrow, color = arrow_color(diff)
        c2.markdown(
            f"""**Clinics per 1,000 People**<br>
            {clinics_per_1000_sel:.2f}<br>
            {arrow} <span style='color:{color}'>{diff:+.2f} vs GTA</span>""",
            unsafe_allow_html=True,
        )
    else:
        c2.metric("Clinics per 1,000 People", "N/A")

    c3, c4 = st.columns(2)
    if pd.notnull(avg_rating_sel) and pd.notnull(gta_avg_rating):
        diff = avg_rating_sel - gta_avg_rating
        arrow, color = arrow_color(diff)
        c3.markdown(
            f"""**Average Clinic Rating**<br>
            {avg_rating_sel:.2f}<br>
            {arrow} <span style='color:{color}'>{diff:+.2f} vs GTA</span>""",
            unsafe_allow_html=True,
        )
    else:
        c3.metric("Average Clinic Rating", "N/A")

    if pd.notnull(reviews_per_1000_sel) and pd.notnull(gta_reviews_per_1000):
        diff = reviews_per_1000_sel - gta_reviews_per_1000
        arrow, color = arrow_color(diff)
        c4.markdown(
            f"""**Reviews per 1,000 People**<br>
            {reviews_per_1000_sel:.1f}<br>
            {arrow} <span style='color:{color}'>{diff:+.1f} vs GTA</span>""",
            unsafe_allow_html=True,
        )
    else:
        c4.metric("Reviews per 1,000 People", "N/A")

    # ---------------------------------------------------------
    # GTA comparison histograms
    # ---------------------------------------------------------
    st.subheader("📈 Comparison to GTA")

    fig, axs = plt.subplots(2, 2, figsize=(12, 10))

    axs[0, 0].hist(df_tmp["PopPerClinic"].dropna(), bins=20, color="skyblue")
    if pd.notnull(pop_per_clinic_sel):
        axs[0, 0].axvline(pop_per_clinic_sel, color="blue", linestyle="--", label="Selected")
    axs[0, 0].set_title("Population per Clinic")
    axs[0, 0].set_xlabel("People per Clinic")
    axs[0, 0].set_ylabel("Number of DGUIDs")
    axs[0, 0].legend()

    row_sel = df_tmp[df_tmp["DGUID"] == dguid]
    selected_clinics_per_1000 = (
        row_sel["ClinicsPer1000"].iloc[0] if not row_sel.empty else clinics_per_1000_sel
    )
    axs[0, 1].hist(df_tmp["ClinicsPer1000"].dropna().clip(upper=10), bins=20, color="lightgreen", alpha=0.7)
    if pd.notnull(selected_clinics_per_1000):
        axs[0, 1].axvline(min(selected_clinics_per_1000, 10), color="darkgreen", linestyle="--", label="Selected")
    axs[0, 1].set_xlim(0, 10)
    axs[0, 1].set_title("Clinics per 1,000 People")
    axs[0, 1].legend()

    valid_ratings = df_tmp["Average_Rating"]
    valid_ratings = valid_ratings[valid_ratings > 0]
    axs[1, 0].hist(valid_ratings, bins=5, color="gold")
    if pd.notnull(avg_rating_sel):
        axs[1, 0].axvline(avg_rating_sel, color="orange", linestyle="--", label="Selected")
    axs[1, 0].set_title("Average Clinic Rating")
    axs[1, 0].legend()

    axs[1, 1].hist(df_tmp["ReviewsPer1000"].dropna().clip(upper=1000), bins=20, color="salmon")
    if pd.notnull(reviews_per_1000_sel):
        axs[1, 1].axvline(min(reviews_per_1000_sel, 1000), color="red", linestyle="--", label="Selected")
    axs[1, 1].set_xlim(0, 1000)
    axs[1, 1].set_title("Reviews per 1,000 People")
    axs[1, 1].legend()

    st.pyplot(fig)
