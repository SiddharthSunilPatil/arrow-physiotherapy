import pandas as pd
import geopandas as gpd

def load_all_data():
    df_reduced = pd.read_csv("data/df_reduced.csv")
    df_reduced.columns = df_reduced.columns.str.strip()  # <--- NEW LINE

    gdf_physio = gpd.read_file("data/gdf_physio_DGUID.geojson")
    gdf_hospitals = gpd.read_file("data/gdf_hospitals_DGUID.geojson")
    return df_reduced, gdf_physio, gdf_hospitals

def load_reviews():
    pcr = pd.read_csv("data/pcr_with_DGUID.csv")
    sfr = pd.read_csv("data/sfr_with_DGUID.csv")
    return pcr, sfr
