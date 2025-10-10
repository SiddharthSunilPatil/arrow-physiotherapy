# app.py
import streamlit as st
import pandas as pd
import requests
import os 

from utils.load_data import load_all_data, load_reviews
from utils.geospatial import get_dguid_from_latlon
from pathlib import Path

from sections import population_stats
from sections import competitors
from sections import hospitals
from sections import sentiment_physio

st.set_page_config(page_title="Arrow Physio Dashboard", layout="wide")
st.title("📍 Arrow Physio Market Insights")

def get_gcp_key():
    """Safely load GCP key from secrets.toml (local) or env var (Cloud Run)."""
    try:
        # Check if Streamlit secrets file exists
        secrets_path = Path("/app/.streamlit/secrets.toml")
        if secrets_path.exists() and "general" in st.secrets and "gcp_api_key" in st.secrets["general"]:
            return st.secrets["general"]["gcp_api_key"]
    except FileNotFoundError:
        pass  # No secrets.toml file on Cloud Run — skip to env var

    # Use environment variable on Cloud Run
    return os.getenv("gcp_api_key")

gcp_api_key = get_gcp_key()

# -------------------------
# Google Maps Geocoding function
# -------------------------
def geocode_address(address, api_key):
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    response = requests.get(url).json()
    if response["status"] == "OK":
        result = response["results"][0]
        location = result["geometry"]["location"]
        formatted_address = result["formatted_address"]
        return location["lat"], location["lng"], formatted_address
    return None, None, None

# -------------------------
# Load data once
# -------------------------
df_reduced, gdf_physio, gdf_hospitals = load_all_data()
pcr_reviews, _ = load_reviews()

# Global display settings
st.session_state["POP_GTA_SCALED"] = True
st.session_state["KPI_ABSOLUTE_ARROW"] = False

# -------------------------
# Initialize session state for location persistence
# -------------------------
if "address" not in st.session_state:
    st.session_state.address = ""
if "lat" not in st.session_state:
    st.session_state.lat = None
if "lon" not in st.session_state:
    st.session_state.lon = None
if "formatted_address" not in st.session_state:
    st.session_state.formatted_address = None
if "run_analysis" not in st.session_state:
    st.session_state.run_analysis = False

# -------------------------
# Address Input (live map preview)
# -------------------------
st.sidebar.header("📍 Location Input")
address_input = st.sidebar.text_input("Enter clinic address", value=st.session_state.address, placeholder="e.g. 125 Bronte Rd, Oakville")

# If user typed a new address → geocode immediately
if address_input != st.session_state.address and address_input.strip() != "":
    api_key = gcp_api_key
    lat, lon, formatted_address = geocode_address(address_input, api_key)

    if lat and lon:
        st.session_state.address = address_input
        st.session_state.lat = lat
        st.session_state.lon = lon
        st.session_state.formatted_address = formatted_address
    else:
        st.warning("Could not find this address. Please check spelling.")
        st.session_state.lat = None
        st.session_state.lon = None
        st.session_state.formatted_address = None
        st.session_state.run_analysis = False

# Show map + formatted address if we have stored coordinates
if st.session_state.lat and st.session_state.lon:
    st.success(f"📍 Matched address: {st.session_state.formatted_address}")
    st.map(pd.DataFrame({'lat': [st.session_state.lat], 'lon': [st.session_state.lon]}), zoom=14)

    # Show analysis button in sidebar
    if st.sidebar.button("🔍 Run Market Analysis"):
        st.session_state.run_analysis = True
else:
    st.info("ℹ️ Enter an address to see live map preview.")

# -------------------------
# Render dashboard if ready
# -------------------------
if st.session_state.run_analysis and st.session_state.lat and st.session_state.lon:
    dguid = get_dguid_from_latlon(st.session_state.lat, st.session_state.lon, df_reduced)

    if dguid:
        st.success(f"✅ DGUID Found: {dguid}")
        population_stats.render(df_reduced, dguid, st.session_state.lat, st.session_state.lon)
        competitors.render(gdf_physio, dguid, st.session_state.lat, st.session_state.lon, df_reduced)
        hospitals.render(st.session_state.lat, st.session_state.lon, dguid, gdf_physio, gdf_hospitals)
        sentiment_physio.render(dguid, pcr_reviews)
    else:
        st.error("❌ No matching DGUID found for the selected location.")
