# Healthcare Location Intelligence Dashboard (LID)

## Business Problem
I was approached by a team of physiotherapists who were planning to open their first clinic in the Greater Toronto Area (GTA). On paper, the GTA looked promising — large population, good incomes, good footfall. But once we started digging, we realized the real problem: **almost every neighbourhood already had clinics**, and each location came with a different challenge — high competition in some areas, weak demographics in others, and in a few cases, very little referral support from nearby hospitals or walk-ins.

## The Solution
So instead of guessing, we decided to **build a dashboard** that could tell us — for any point in the GTA — “what does the market around this place look like?” After a couple of iterations and requirement-gathering sessions, we arrived at the idea of a **geospatial, data-driven location planner**:

- pull census-level demographics from **Statistics Canada** for the exact area of interest,
- map nearby **competitor clinics, hospitals, and walk-in centres** via the **Google Places API**,
- and (later) layer in **sentiment analysis of Google reviews** to understand how existing clinics are performing.

That’s how the **Location Intelligence Dashboard (LID)** was born — a tool to take the guesswork out of clinic expansion. You can check how the dashboard works by clicking on the URL below or check the screenshots below to see how the dashboard looks.

## Url : https://arrow-dashboard-93638475280.us-central1.run.app/

## Screenshots

## 1. User Interface to enter address of interest and confirm map location
![image](https://github.com/SiddharthSunilPatil/arrow-physiotherapy/blob/main/screenshots/Screenshot_001.png)

## 2. Demographic information within selected radius along with GTA metrics comparison
![image](https://github.com/SiddharthSunilPatil/arrow-physiotherapy/blob/main/screenshots/Screenshot_002.png)

## 3. Competitor data within selected radius
![image](https://github.com/SiddharthSunilPatil/arrow-physiotherapy/blob/main/screenshots/Screenshot_003.png)

## 4. Spatial distribution of competitors and location of interest
![image](https://github.com/SiddharthSunilPatil/arrow-physiotherapy/blob/main/screenshots/Screenshot_004.png)

## 5. Feature engineered metrics
![image](https://github.com/SiddharthSunilPatil/arrow-physiotherapy/blob/main/screenshots/Screenshot_005.png)

## 6. Patient Sentiment Analysis
![image](https://github.com/SiddharthSunilPatil/arrow-physiotherapy/blob/main/screenshots/Screenshot_006.png)

---

## Project Overview
The Location Intelligence Dashboard is a Streamlit-based, cloud-ready app that lets a clinic owner, operations head, or analyst:
- enter a location (lat/long),
- map it to the correct **StatsCan census/DGUID** using geospatial tools,
- fetch the corresponding **demographic, income, and population** metrics,
- and overlay **competitor and healthcare facility density** to understand how viable that location is.

It was initially built for a physiotherapy clinic in the GTA but designed so it can be generalized to other healthcare practices.

---

## Key Features
- **Census & Demographic Intelligence**  
  Pulls population, age, gender, income, and growth info from preprocessed StatsCan data at a census/DGUID level.
- **Competitor & Support Mapping**  
  Uses Google Places API and prebuilt GeoDataFrames to show nearby physiotherapy clinics, hospitals, and walk-in clinics.
- **Business KPIs**  
  - clinic-to-population ratio  
  - hospital-to-physio ratio  
  - competitor count within selected radius  
  - GTA average vs selected location
- **Interactive Geospatial Visuals**  
  Map layers built using PyDeck / Folium for quick visual inspection.
- **Sentiment (Planned/Experimental)**  
  Hook to run sentiment on Google reviews of nearby clinics to understand service quality, not just quantity.
- **Deployment Friendly**  
  Built on Streamlit and deployed to Google Cloud (can also run locally).

---

## Project Architecture (High Level)
1. **Input**: User enters/selects latitude & longitude.
2. **Geospatial Mapping**: Location is mapped to the corresponding Statistics Canada DGUID (census geography).
3. **Data Fetching**:
   - demographics from `df_reduced`
   - nearby physio clinics from `gdf_physio_DGUID`
   - nearby hospitals/walk-ins from `gdf_hospitals_DGUID`
   - (optional) live Places API calls
4. **Feature Engineering**:
   - derive clinic-to-population, hospital-to-clinic, and saturation indicators
   - compare with GTA-level means (Mississauga, Oakville, Burlington, Etobicoke treated as GTA)
5. **Visualization**:
   - Streamlit dashboard with KPIs, maps, and tables
6. **(Future)** ML layer:
   - no-show prediction
   - clinic success prediction
   - smart scheduling suggestions

---

## Tech Stack
- **Language & App:** Python, Streamlit
- **Geospatial:** GeoPandas, Shapely, PyDeck, Folium
- **Data Sources:** Statistics Canada census (preprocessed), Google Places API
- **Data Handling:** Pandas, NumPy
- **Deployment:** Google Cloud (Cloud Run / VM) / Streamlit Cloud
- **Version Control:** GitHub

---
## Setup Instructions

**1. Cloning the repository**

1.1. Create a directory on your local drive where you want to store the project.  
1.2. Open Anaconda Prompt (or terminal) and navigate to the directory using: cd <your-directory-path>  
1.3. Launch VS Code from this directory using: code .  
1.4. Open a new terminal in VS Code and clone the repository using: git clone https://github.com/<your-username>/<repository-name>.git  

**2. Setting up the environment**

2.1. Navigate to the cloned repository: cd <repository-name>  
2.2. Create a virtual environment: conda create -p venv python=3.9 -y  
2.3. Activate the environment: conda activate venv/  

**3. Installing dependencies**

3.1. Install all required dependencies using: pip install -r requirements.txt  

**4. Configuring API keys and secrets**

4.1. Inside the repository, create the following folder if it does not already exist: .streamlit/  
4.2. Inside .streamlit/, create a file named secrets.toml  
4.3. Add your Google Places API key in the following format:places_api_key = "YOUR_GOOGLE_PLACES_API_KEY"  
⚠️ Note: Do not commit secrets.toml to GitHub  
This file is required for live competitor and hospital lookup  

**5. Verifying data availability**

5.1. Ensure the following data files exist in the data/ directory:  
df_reduced.parquet (Statistics Canada census data)  
gdf_physio_DGUID.parquet (physiotherapy clinics)  
gdf_hospitals_DGUID.parquet (hospitals & walk-in clinics)  

These files are preprocessed and required for the dashboard to function correctly.  

**6. Running the application locally**

6.1. Execute the following command to launch the Streamlit app: streamlit run app.py  
   
## Repository Structure
```text
.
├── app.py                     # main Streamlit app
├── requirements.txt
├── config/                    # config, constants (no secrets)
├── data/
│   ├── df_reduced.parquet     # StatsCan GTA-level processed data
│   ├── gdf_physio_DGUID.parquet
│   └── gdf_hospitals_DGUID.parquet
├── sections/
│   ├── population_stats.py
│   ├── competitors.py
│   └── hospitals.py
├── utils/
│   ├── load_data.py
│   ├── geoutils.py
│   └── kpi_utils.py
├── .streamlit/
│   └── secrets.toml
└── README.md

