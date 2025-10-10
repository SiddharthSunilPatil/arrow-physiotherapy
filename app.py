# app.py
import streamlit as st
import pandas as pd
import requests
import os 
from pathlib import Path

from utils.load_data import load_all_data, load_reviews
from utils.geospatial import get_dguid_from_latlon
from sections import population_stats, competitors, hospitals, sentiment_physio

st.set_page_config(page_title="Arrow Physio Dashboard", layout="wide")
st.title("📍 Arrow Physio Market Insights")

def get_gcp_key():
    """Safely load GCP key from secrets.toml (local) or env var (Cloud Run)."""
    try:
        secrets_path = Path("/app/.streamlit/secrets.toml")
        if secrets_path.exists() and "general" in st.secrets and "gcp_api_key" in st.secrets["general"]:
            return st.secrets["general"]["gcp_api_key"]
    except FileNotFoundError:
        pass
    return os.getenv("gcp_api_key")

gcp_api_key = get_gcp_key()

def geocode_address(address, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    response = requests.get(url).json()
    if response["status"] == "OK":
        result = response["results"][0]
        location = result["geometry"]["location"]
        return location["lat"], location["lng"], result["formatted_address"]
    return None, None, None

# Load data once
df_reduced, gdf_physio, gdf_hospitals = load_all_data()
pcr_reviews, _ = load_reviews()

# Session state
for key in ["address", "lat", "lon", "formatted_address", "run_analysis"]:
    if key not in st.session_state:
        st.session_state[key] = "" if key == "address" else None

# ------------------------- MAIN UI -------------------------

st.subheader("🏠 Step 1: Enter Clinic Address")
address_input = st.text_input(
    "Enter clinic address",
    value=st.session_state.address,
    placeholder="e.g. 125 Bronte Rd, Oakville"
)

if address_input != st.session_state.address and address_input.strip():
    lat, lon, formatted_address = geocode_address(address_input, gcp_api_key)
    if lat and lon:
        st.session_state.update({
            "address": address_input,
            "lat": lat,
            "lon": lon,
            "formatted_address": formatted_address
        })
    else:
        st.warning("❌ Could not find this address. Please check spelling.")
        st.session_state.lat = st.session_state.lon = st.session_state.formatted_address = None
        st.session_state.run_analysis = False

if st.session_state.lat and st.session_state.lon:
    st.success(f"📍 {st.session_state.formatted_address}")
    st.map(pd.DataFrame({'lat': [st.session_state.lat], 'lon': [st.session_state.lon]}), zoom=14)

    if st.button("🔍 Run Market Analysis"):
        st.session_state.run_analysis = True
else:
    st.info("ℹ️ Type an address above to see map preview.")

# ------------------------- ANALYSIS -------------------------

if st.session_state.run_analysis and st.session_state.lat and st.session_state.lon:
    dguid = get_dguid_from_latlon(st.session_state.lat, st.session_state.lon, df_reduced)
    if dguid:
        st.success(f"✅ DGUID Found: {dguid}")
        population_stats.render(df_reduced, dguid, st.session_state.lat, st.session_state.lon)
        competitors.render(gdf_physio, dguid, st.session_state.lat, st.session_state.lon, df_reduced)
        hospitals.render(st.session_state.lat, st.session_state.lon, dguid, gdf_physio, gdf_hospitals)
        sentiment_physio.render(dguid, pcr_reviews)
    else:
        st.error("❌ No matching DGUID found for this location.")
