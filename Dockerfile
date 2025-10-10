# Use a geospatial-ready base image (includes GDAL, PROJ, GEOS, etc.)
FROM ghcr.io/osgeo/gdal:alpine-small-latest

# Install Python and build tools
RUN apk add --no-cache python3 py3-pip py3-numpy py3-pandas py3-requests \
    py3-geopandas py3-shapely py3-fiona py3-pyproj py3-psycopg2 \
    g++ && \
    ln -sf python3 /usr/bin/python && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app
COPY . /app

# Install only the remaining Python libs not provided above
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
