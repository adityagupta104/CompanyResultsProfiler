import streamlit as st
import pandas as pd
from bse_core import get_range_quarters_data, pivot_announcement_links, search_bse_company
import re

PDF_ICON_URL = "https://upload.wikimedia.org/wikipedia/commons/6/60/Adobe_Acrobat_Reader_icon_%282020%29.svg"

# ------------------------------
# Helper to convert links to PDF icons
# ------------------------------
def render_pivot_html_with_icons(pivot_df):
    """
    Convert MultiIndex pivot_df to HTML where each cell shows PDF icon(s)
    with Headline tooltip on hover.
    """
    html_df = pivot_df.copy()

    for col in pivot_df.columns.levels[1]:  # iterate over quarters
        link_col = ("Link", col)
        headline_col = ("Headline", col)

        if link_col in pivot_df.columns and headline_col in pivot_df.columns:
            html_df[link_col] = pivot_df.apply(
                lambda row: " ".join(
                    f'<a href="{url}" target="_blank" title="{title}">'
                    f'<img src="{PDF_ICON_URL}" width="20" height="20"></a>'
                    for url, title in zip(row[link_col] or [], row[headline_col] or [])
                    if url
                ),
                axis=1
            )

    # Only keep Link level for rendering
    html_render = html_df["Link"]
    return html_render.to_html(escape=False)

# ------------------------------
# Quarter sorting helper
# ------------------------------
def quarter_sort_key(q):
    match = re.match(r"Q(\d) FY(\d+)", q)
    if match:
        q_num = int(match.group(1))
        fy_year = int(match.group(2))
        return (fy_year, q_num)
    return (0, 0)

# ------------------------------
# Wrapper for core bse functions with caching
# Caching search results for 1 day
# ------------------------------
@st.cache_data(ttl=86400)  # 1 day cache
def search_bse_company_cached(company_input):
    return search_bse_company(company_input)
    
# ------------------------------
# Wrapper for core bse functions with caching
# Caching search results for 1 day
# ------------------------------
@st.cache_data(ttl=86400)  # 1 day cache
def get_range_quarters_data_cached(scrip_code, start_quarter, start_fy, end_quarter, end_fy, configs):
    return get_range_quarters_data(scrip_code, start_quarter, start_fy, end_quarter, end_fy, configs)

# ------------------------------
# Session state init
# ------------------------------
if "scrip_code" not in st.session_state:
    st.session_state.scrip_code = None
if "company_name" not in st.session_state:
    st.session_state.company_name = ""
if "matches" not in st.session_state:
    st.session_state.matches = []


# ------------------------------
# Step 1: Company Search
# ------------------------------
st.title("BSE Data Viewer")

company_input = st.text_input("Enter Company Name", value="HDFC")
search_button = st.button("Search Company")

if search_button and company_input:
    matches = search_bse_company_cached(company_input.lower())
    st.session_state.matches = matches  # save in session_state
    if not matches:
        st.warning("No matches found. Please refine your search.")


# ------------------------------
# Step 2: Company selection dropdown
# ------------------------------
selected_company = None
if st.session_state.matches:
    options = [f"{m['name']} ({m['scrip_code']})" for m in st.session_state.matches]
    selection = st.selectbox("Select a company from the matches", options)
    
    # Extract scrip_code from selection
    scrip_code = selection.split("(")[-1].strip(")")
    st.session_state.scrip_code = scrip_code
    st.session_state.company_name = selection.split("(")[0].strip()
    selected_company = st.session_state.company_name


# ------------------------------
# Step 3: Show rest only if company selected
# ------------------------------
if selected_company:
    st.subheader(f"Fetching BSE data for: {selected_company}")

    # Quarter & FY inputs
    col1, col2 = st.columns(2)
    start_quarter = col1.number_input("Start Quarter (1-4)", min_value=1, max_value=4, value=1)
    start_fy = col2.number_input("Start Fiscal Year", min_value=2000, max_value=2100, value=2024)

    col3, col4 = st.columns(2)
    end_quarter = col3.number_input("End Quarter (1-4)", min_value=1, max_value=4, value=2)
    end_fy = col4.number_input("End Fiscal Year", min_value=2000, max_value=2100, value=2026)

# Check if the selected range exceeds 5 years
    total_years = end_fy - start_fy + 1
    if total_years > 5:
        st.error("Please select a range of **at most 5 fiscal years**.")
    else:
        # Example configs
        configs = [
            {"name": "Results", "category": "Result", "lookahead": True},  
            {"name": "Results", "category": "Board Meeting", "filter": "result", "lookahead": True},  
            {"name": "Presentation", "category": "Company Update", "filter": "presentation", "lookahead": True},
            {"name": "Transcript", "category": "Company Update", "filter": "transcript", "lookahead": True},
            {"name": "Insider trading", "category": "Insider Trading / SAST"},
            {"name": "Press Release", "category": "Company Update", "filter": "press release"},
            {"name": "Resignations", "category": "Company Update", "filter": "resignation"}
        ]

        # Fetch button
        fetch_button = st.button("Fetch BSE Data")
        if fetch_button:
            with st.spinner("Fetching data..."):
                df = get_range_quarters_data_cached(scrip_code, start_quarter, start_fy, end_quarter, end_fy, configs)
                
                if df.empty:
                    st.warning("No data found for this company and date range.")
                else:
                    pivot_df = pivot_announcement_links(df, configs)
                    
                    # Sort columns by fiscal year and quarter
                    pivot_df = pivot_df.sort_index(
                        axis=1,
                        level=1,
                        key=lambda x: x.map(quarter_sort_key),
                        ascending=True
                    )

                    pivot_html = render_pivot_html_with_icons(pivot_df)

                    st.success("Data fetched!")
                    st.markdown("### Key documents uploaded to BSE")
                    st.markdown(pivot_html, unsafe_allow_html=True)
