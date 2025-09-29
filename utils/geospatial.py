import geopandas as gpd
from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads

def get_dguid_from_latlon(lat, lon, df_reduced):
    """
    Given a lat/lon and df_reduced, return the DGUID of the matching census tract.
    """
    # Convert geometry column if needed
    if not isinstance(df_reduced, gpd.GeoDataFrame):
        df_reduced['geometry'] = df_reduced['geometry'].apply(wkt_loads)
        df_reduced = gpd.GeoDataFrame(df_reduced, geometry='geometry', crs='EPSG:4326')

    # Create point from input
    point = Point(lon, lat)

    # Spatial match
    match = df_reduced[df_reduced.geometry.contains(point)]

    if not match.empty:
        return match.iloc[0]['DGUID']
    else:
        return None
