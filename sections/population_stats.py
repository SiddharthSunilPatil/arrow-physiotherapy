import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def render(df_reduced, dguid):
    st.header("👥 Population & Demographics")

    # Filter for selected DGUID
    row = df_reduced[df_reduced['DGUID'] == dguid]
    if row.empty:
        st.warning("No demographic data found for this DGUID.")
        return

    row = row.iloc[0]
    gta = df_reduced.mean(numeric_only=True)

    # === Key Stats ===
    st.subheader("📌 Key Stats")
    col1, col2, col3 = st.columns(3)

    pop_2021 = row["Population, 2021"]
    col1.metric("Population (2021)", f"{int(pop_2021)}" if pd.notnull(pop_2021) else "N/A")

    # --- Population Growth
    growth = row['Population percentage change, 2016 to 2021']
    gta_growth = gta['Population percentage change, 2016 to 2021']
    diff_growth = growth - gta_growth
    arrow_growth = "⬆️" if diff_growth > 0 else "⬇️"
    color_growth = "green" if diff_growth > 0 else "red"
    col2.markdown(f"""**Population Growth**<br>{growth:.1f}%<br>{arrow_growth} <span style='color:{color_growth}'>{diff_growth:+.1f}% vs GTA</span>""", unsafe_allow_html=True)

    # --- Population Density
    density = row['Population density per square kilometre']
    gta_density = gta['Population density per square kilometre']
    diff_density = density - gta_density
    arrow_density = "⬆️" if diff_density > 0 else "⬇️"
    color_density = "green" if diff_density > 0 else "red"
    col3.markdown(f"""**Population Density**<br>{density:.1f} ppl/km²<br>{arrow_density} <span style='color:{color_density}'>{diff_density:+.0f} vs GTA</span>""", unsafe_allow_html=True)

    # === Income Stats ===
    st.subheader("💰 Income Comparison")
    col4, col5 = st.columns(2)

    median_income = row['Median total income in 2020 among recipients ($)']
    gta_median = gta['Median total income in 2020 among recipients ($)']
    diff_median = median_income - gta_median
    arrow_median = "⬆️" if diff_median > 0 else "⬇️"
    color_median = "green" if diff_median > 0 else "red"
    col4.markdown(
        f"""<div style='font-size:18px;'><strong>Median Income (2020)</strong><br>
        ${int(median_income):,}<br>
        {arrow_median} <span style='color:{color_median}'>${diff_median:,.0f} vs GTA</span>
        </div>""", unsafe_allow_html=True)

    avg_income = row['Average total income in 2020 among recipients ($)']
    gta_avg = gta['Average total income in 2020 among recipients ($)']
    diff_avg = avg_income - gta_avg
    arrow_avg = "⬆️" if diff_avg > 0 else "⬇️"
    color_avg = "green" if diff_avg > 0 else "red"
    col5.markdown(
        f"""<div style='font-size:18px;'><strong>Average Income (2020)</strong><br>
        ${int(avg_income):,}<br>
        {arrow_avg} <span style='color:{color_avg}'>${diff_avg:,.0f} vs GTA</span>
        </div>""", unsafe_allow_html=True)

    # === Age, Income & Growth Histograms ===
    st.subheader("📊 Demographic Distributions")

    age_labels = ['0 to 14 years', '15 to 64 years', '65 years and over', '85 years and over']
    age_values = [row[label] if pd.notnull(row[label]) else 0 for label in age_labels]
    income_data = df_reduced[["Median total income in 2020 among recipients ($)", "Average total income in 2020 among recipients ($)"]].dropna()
    growth_data = df_reduced["Population percentage change, 2016 to 2021"].dropna()

    fig, axs = plt.subplots(2, 2, figsize=(12, 10))

    # Age Distribution
    axs[0, 0].bar(age_labels, age_values, color='skyblue')
    axs[0, 0].set_ylabel("Population Count")
    axs[0, 0].set_title("Age Distribution")

    # Income Distribution
    axs[0, 1].hist(income_data["Median total income in 2020 among recipients ($)"], bins=20, alpha=0.6, label="Median Income", color='skyblue')
    axs[0, 1].hist(income_data["Average total income in 2020 among recipients ($)"], bins=20, alpha=0.6, label="Average Income", color='orange')
    if pd.notnull(median_income):
        axs[0, 1].axvline(median_income, color='blue', linestyle='--', linewidth=2, label='Selected DGUID Median')
    if pd.notnull(avg_income):
        axs[0, 1].axvline(avg_income, color='darkorange', linestyle='--', linewidth=2, label='Selected DGUID Average')
    axs[0, 1].set_xlabel("Income ($)")
    axs[0, 1].set_ylabel("Number of DGUIDs")
    axs[0, 1].set_title("Income Distribution")
    axs[0, 1].legend()

    # Population Growth Distribution
    axs[1, 0].hist(growth_data, bins=20, color='green', alpha=0.7)
    if pd.notnull(growth):
        axs[1, 0].axvline(growth, color='darkgreen', linestyle='--', linewidth=2, label='Selected DGUID')
    axs[1, 0].set_xlabel("Growth % (2016–2021)")
    axs[1, 0].set_ylabel("Number of DGUIDs")
    axs[1, 0].set_title("Population Growth Distribution")
    axs[1, 0].legend()

    axs[1, 1].axis('off')
    st.pyplot(fig)
