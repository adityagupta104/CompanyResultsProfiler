import requests
from bse_core import get_range_quarters_data, search_bse_company
from genai_extract_results import get_extracted_results, json_to_dataframe
import pandas as pd
from io import BytesIO
import streamlit as st
import re  

PDF_ICON_URL = "https://upload.wikimedia.org/wikipedia/commons/6/60/Adobe_Acrobat_Reader_icon_%282020%29.svg"

configs = [
        {"name": "Results", "category": "Result", "lookahead": True},  
        {"name": "Results", "category": "Board Meeting", "filter": "result", "lookahead": True},  
        {"name": "Presentation", "category": "Company Update", "filter": "presentation", "lookahead": True},
        {"name": "Transcript", "category": "Company Update", "filter": "transcript", "lookahead": True},
        {"name": "Insider trading", "category": "Insider Trading / SAST"},
        {"name": "Press Release", "category": "Company Update", "filter": "press release"},
        {"name": "Resignations", "category": "Company Update", "filter": "resignation"}
]

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


#------------------------------
# Extract results from PDF link using Gemini
#------------------------------
def extract_results_from_pdf_link(extract_selected_quarter, type, pdf_link, user_api_key):
    """
    Given a PDF link, fetch the PDF and extract financial results using Google Gemini.
    type - consolidated or standalone
    """
    quarter, year = extract_selected_quarter.split()  # "Q2", "FY2024"                      
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Download PDF into BytesIO
    pdf_response = requests.get(pdf_link, allow_redirects=True, headers=headers)
    pdf_response.raise_for_status()
    pdf_bytes = BytesIO(pdf_response.content)

    # Call Gemini to extract results
    response = get_extracted_results(quarter, year, type, pdf_bytes, api_key=user_api_key)

    # Convert JSON to DataFrame
    df_results = json_to_dataframe(response.text)
    df_results.rename(columns={"Value": f'{extract_selected_quarter}'}, inplace=True)

    # Clean up the extracted column
    col = extract_selected_quarter
    if col in df_results.columns:
        # Replace blank strings and whitespace-only strings with np.nan
        # df_results[col] = df_results[col].replace(r'^\s*$', np.nan, regex=True)
        # Optionally, convert to numeric where possible (non-convertible values become NaN)
        df_results[col] = pd.to_numeric(df_results[col], errors='coerce')

    return df_results
    

# ------------------------------
# Pivot announcement links
# ------------------------------
def pivot_announcement_links(df, configs):
    """
    Pivot DataFrame to have Configs as rows and Quarter_FY as columns.
    Each cell contains clickable links.
    """
    if df.empty:
        return pd.DataFrame()
    
    unique_config_order = []
    seen = set()
    for cfg in configs:
        if cfg["name"] not in seen:
            unique_config_order.append(cfg["name"])
            seen.add(cfg["name"])

    df["Config"] = pd.Categorical(df["Config"], categories=unique_config_order, ordered=True)

    df["Quarter_FY"] = df.apply(lambda x: f"Q{x.Quarter} FY{x.FiscalYear}", axis=1)

    pivot_df = df.pivot_table(
        index="Config",
        columns="Quarter_FY",
        values=["Link", "Headline"],
        aggfunc=lambda x: list(x)
        #aggfunc=lambda links: "\n".join([f"{l}" for l in links if l])
    ).fillna("")

    # Sort columns by fiscal year and quarter
    pivot_df = pivot_df.sort_index(
        axis=1,
        level=1,
        key=lambda x: x.map(quarter_sort_key),
        ascending=True
    )

    return pivot_df

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
