import streamlit as st
from utils.load_data import load_all_data, load_reviews
from utils.geospatial import get_dguid_from_latlon
from sections import population_stats, competitors, hospitals, sentiment_physio

st.set_page_config(page_title="Arrow Physio Dashboard", layout="wide")

st.title("📍 Arrow Physio Market Insights")

# === Input fields ===
lat = st.number_input("Enter Latitude", format="%.6f")
lon = st.number_input("Enter Longitude", format="%.6f")

# === Load data once ===
df_reduced, gdf_physio, gdf_hospitals = load_all_data()
pcr_reviews,sfr_reviews=load_reviews()


# === Only act if both lat & lon are entered ===
if lat != 0.0 and lon != 0.0:
    dguid = get_dguid_from_latlon(lat, lon, df_reduced)

    if dguid:
        st.success(f"✅ DGUID Found: {dguid}")
        population_stats.render(df_reduced, dguid)
        # Pass df_reduced to competitors
        competitors.render(gdf_physio, dguid, lat, lon, df_reduced)
        hospitals.render(lat, lon, dguid, gdf_physio, gdf_hospitals)
        sentiment_physio.render(dguid, pcr_reviews) 
    else:
        st.error("❌ No matching DGUID found for the entered coordinates.")
else:
    st.info("ℹ️ Please enter both latitude and longitude to view the report.")
