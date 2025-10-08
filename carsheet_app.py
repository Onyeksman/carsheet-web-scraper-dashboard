import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO, BytesIO
import plotly.express as px
import numpy as np

# -----------------------------------------------------
# SCRAPING CONFIGURATION
# -----------------------------------------------------
BASE_URL = "https://carsheet.io/aston-martin,audi,bentley,bmw,ferrari,ford,mercedes-benz/2024/2-door/"


# -----------------------------------------------------
# SCRAPER FUNCTION
# -----------------------------------------------------
def scrape_all_pages():
    """Scrape all pages from carsheet.io and return a combined DataFrame."""
    session = requests.Session()
    all_dfs = []
    page_num = 1

    while True:
        st.write(f"🔎 Scraping page {page_num} ...")

        try:
            resp = session.get(BASE_URL, params={"page": page_num}, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            })
            resp.raise_for_status()
        except requests.RequestException as e:
            st.error(f"❌ Error fetching page {page_num}: {e}")
            break

        # Parse HTML
        soup = BeautifulSoup(resp.text, "html.parser")

        # Read HTML table safely
        tables = pd.read_html(StringIO(resp.text))
        if not tables:
            st.warning("⚠️ No tables found, stopping.")
            break

        df = tables[0]
        df.columns = [str(c).strip() for c in df.columns]
        all_dfs.append(df)

        # Detect pagination
        next_btn = soup.select_one("li.paginate_button.page-item.next")
        if not next_btn or "disabled" in next_btn.get("class", []):
            st.success("✅ Last page reached.")
            break

        page_num += 1

    return pd.concat(all_dfs, ignore_index=True) if all_dfs else None


# -----------------------------------------------------
# STREAMLIT DASHBOARD CONFIG
# -----------------------------------------------------
st.set_page_config(page_title="Carsheet Data Explorer", layout="wide")
st.title("🚗 Carsheet Web Scraper Dashboard (2024 Two-Door Models)")
st.markdown("Scrape and explore car specifications directly from **carsheet.io** in a single dashboard.")

# Initialize session state
if "df" not in st.session_state:
    st.session_state.df = None

# Sidebar controls
st.sidebar.header("⚙️ Controls")

# Start scraping button
if st.sidebar.button("🕹️ Start Scraping Carsheet Data"):
    with st.spinner("Scraping data... please wait ⏳"):
        df = scrape_all_pages()
    if df is not None:
        st.session_state.df = df
        st.success("✅ Scraping completed successfully!")

# Clear cache button
if st.sidebar.button("🧹 Clear Cached Data"):
    st.session_state.df = None
    st.rerun()


# -----------------------------------------------------
# DISPLAY AND FILTER SECTION
# -----------------------------------------------------
if st.session_state.df is not None:
    df = st.session_state.df

    st.subheader("📊 Raw Data Preview")
    st.dataframe(df.head(20), use_container_width=True)

    # Filtering Section
    st.markdown("### 🔍 Filter Data")
    cols = list(df.columns)

    if cols:
        selected_col = st.selectbox("Choose column to filter by:", cols)
        search_term = st.text_input("Enter search term:")

        if search_term:
            filtered_df = df[df[selected_col].astype(str).str.contains(search_term, case=False, na=False)]
        else:
            filtered_df = df

        st.write(f"Showing {len(filtered_df)} results.")
        st.dataframe(filtered_df, use_container_width=True)

        # Prepare Excel for download
        excel_buffer = BytesIO()
        filtered_df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)

        st.download_button(
            label="📥 Download Filtered Data as Excel",
            data=excel_buffer,
            file_name="filtered_cars.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # -----------------------------------------------------
        # 🎛️ DYNAMIC INTERACTIVE VISUAL INSIGHTS (Plotly)
        # -----------------------------------------------------
        st.markdown("### 📈 Visual Insights (Dynamic)")

        # Detect candidate columns
        numeric_cols = [c for c in filtered_df.columns if pd.api.types.is_numeric_dtype(filtered_df[c])]
        possible_price_cols = [c for c in filtered_df.columns if any(k in c.lower() for k in ["price", "cost", "msrp", "value"])]
        possible_brand_cols = [c for c in filtered_df.columns if any(k in c.lower() for k in ["brand", "make", "manufacturer", "model"])]

        # Try to clean numeric-looking price columns
        for col in possible_price_cols:
            if col not in numeric_cols:
                try:
                    filtered_df[col] = (
                        filtered_df[col]
                        .astype(str)
                        .str.replace(r"[^\d.]", "", regex=True)
                        .replace("", np.nan)
                        .astype(float)
                    )
                    numeric_cols.append(col)
                except Exception:
                    pass

        # Final clean list
        numeric_cols = list(set(numeric_cols))
        brand_col = possible_brand_cols[0] if possible_brand_cols else None

        if brand_col and numeric_cols:
            st.success(f"✅ Detected brand column: **{brand_col}**")

            # ---- User Controls ----
            y_col = st.selectbox("Select numeric column for analysis (Y-axis):", numeric_cols)
            agg_func = st.selectbox("Choose aggregation:", ["Count", "Average", "Sum", "Median"])
            chart_type = st.radio("Chart type:", ["Bar Chart", "Box Plot"], horizontal=True)

            # ---- Aggregation Logic ----
            if agg_func == "Count":
                agg_df = filtered_df.groupby(brand_col, as_index=False)[y_col].count()
                agg_df.columns = [brand_col, "Count"]
                y_axis = "Count"
            elif agg_func == "Average":
                agg_df = filtered_df.groupby(brand_col, as_index=False)[y_col].mean()
                y_axis = y_col
            elif agg_func == "Sum":
                agg_df = filtered_df.groupby(brand_col, as_index=False)[y_col].sum()
                y_axis = y_col
            else:
                agg_df = filtered_df.groupby(brand_col, as_index=False)[y_col].median()
                y_axis = y_col

            # ---- Dynamic Plotly Visualization ----
            if chart_type == "Bar Chart":
                fig = px.bar(
                    agg_df.sort_values(y_axis, ascending=False),
                    x=brand_col,
                    y=y_axis,
                    color=y_axis,
                    color_continuous_scale="Viridis",
                    title=f"{agg_func} of {y_col} by {brand_col}",
                    text_auto=True,
                )
            else:
                fig = px.box(
                    filtered_df,
                    x=brand_col,
                    y=y_col,
                    color=brand_col,
                    title=f"Distribution of {y_col} by {brand_col}",
                )

            fig.update_layout(
                title_x=0.5,
                height=600,
                margin=dict(l=40, r=40, t=60, b=40),
                xaxis_title=brand_col,
                yaxis_title=y_axis,
            )
            st.plotly_chart(fig, use_container_width=True)

        elif not brand_col:
            st.info("ℹ️ No brand/manufacturer/model column detected for visualization.")
        else:
            st.info("ℹ️ No numeric columns detected for visualization.")
else:
    st.info("👉 Click **Start Scraping Carsheet Data** in the sidebar to begin.")

# Footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit and Plotly | Data source: carsheet.io")
