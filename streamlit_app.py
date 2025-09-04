
import traceback
import streamlit as st
import os

from dotenv import load_dotenv

from streamlit_app_state import StreamlitAppState
from streamlit_helpers import configs, extract_results_from_pdf_link, pivot_announcement_links, quarter_sort_key, get_range_quarters_data_cached, render_pivot_html_with_icons, search_bse_company_cached



load_dotenv()  # take environment variables from .env file, only needed for my local purpose

app_state = StreamlitAppState() # Initialize session state manager

# ------------------------------
# UI for company search and selection
# ------------------------------
def company_select_section():
    # Step 1: Company Search
    company_input = st.text_input("Enter Company Name", value="Britannia",)
    search_button = st.button("Search Company")

    if search_button and company_input:
        # invalidate previous data
        app_state.reset_all() # new company search, reset all state
        app_state.company_matches = search_bse_company_cached(company_input.lower())
        if not app_state.company_matches:
            st.warning("No matches found. Please refine your search.")

    # Step 2: Company selection dropdown
    # if company search gave any matches, then give the user selection
    # set scrip_code and company_name in session state based on selection
    if app_state.company_matches:
        options = [f"{m['name']} ({m['scrip_code']})" for m in app_state.company_matches]
        selection = st.selectbox("Select a company from the matches", options)
    
        # Extract scrip_code from selection
        app_state.scrip_code = selection.split("(")[-1].strip(")")
        app_state.company_name = selection.split(" ")[0].strip()

# ------------------------------
# UI to Fetch BSE documents section
# ------------------------------
def fetch_bse_documents_section():
    st.subheader(f"Fetch BSE Documents for {app_state.company_name} ({app_state.scrip_code})")

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
    
    # Fetch button
    fetch_button = st.button("Fetch BSE Data")

    if fetch_button and total_years <= 5:
        with st.spinner("Fetching data..."):
            app_state.reset_bse_documents_and_extracted_results() # reset previous documents and extracted results
            app_state.bse_documents_df = get_range_quarters_data_cached(app_state.scrip_code, start_quarter, start_fy, end_quarter, end_fy, configs)

    if app_state.bse_documents_df is not None:
        if app_state.bse_documents_df.empty:
            st.warning("No data found for this company and date range.")
        else:
            app_state.bse_documents_pivot_df = pivot_announcement_links(app_state.bse_documents_df, configs)
            pivot_html = render_pivot_html_with_icons(app_state.bse_documents_pivot_df)

            st.success("Data fetched!")
            st.markdown("### Key documents uploaded to BSE")
            st.markdown(pivot_html, unsafe_allow_html=True)

def extract_results_section():
    # Extract available quarters
    st.markdown("### Extract Financial Results using Google Gemini")
    available_quarters = app_state.bse_documents_pivot_df.columns.levels[1]
    st.write("Results extraction wont work for Banks/NBFCs/Financials, yet!")
    app_state.extract_selected_quarter = st.selectbox("Select a Quarter to Extract Financials", sorted(available_quarters, key=quarter_sort_key, reverse=True))
    app_state.extract_type = st.selectbox("Select which results you want to extract", ["Consolidated", "Standalone"])

    # Conditional API key input for the user
    if os.getenv("GEMINI_API_KEY") is None:
        user_api_key = ""
        st.write("Provide your Google Gemini Key to extract results. If you dont have it, sign up at https://aistudio.google.com/apikey to get free access to Gemini-2.5-flash model.")
        user_api_key = st.text_input("Enter your Google Gemini API Key", type="password", value="")
    else:
        user_api_key = os.getenv("GEMINI_API_KEY")
        st.info("Using GEMINI_API_KEY from environment.")

    extract_results = st.button("Extract Results")
    if extract_results:
        app_state.reset_extracted_results() # reset previous extracted results
        if user_api_key == "":
            st.warning("Please provide your Google Gemini API key to proceed.")
        else:
            app_state.extract_link_count = 0
            extract_results_from_pdf_ui(user_api_key)

    # Display extracted results if available
    if app_state.extracted_results is not None:
        st.subheader(f'Extracted Financials for {app_state.extract_selected_quarter}')
        st.dataframe(app_state.extracted_results)

        if (
            app_state.extracted_results.empty
            or app_state.extract_selected_quarter not in app_state.extracted_results.columns
            or app_state.extracted_results[app_state.extract_selected_quarter].fillna(0).sum() == 0
        ):
            next_pdf_link = app_state.extract_link_count+1
            st.warning(f'No results extracted. You can try with the next PDF[{next_pdf_link}] link for this quarter if available.')   
            try_next_pdf_file = st.button(f'Got Empty Results, Try Next PDF[{next_pdf_link}] Link for this Quarter?')
            if try_next_pdf_file:
                app_state.extract_link_count += 1
                extract_results_from_pdf_ui(user_api_key)
                # we may have new data, repaint, dont know why it needs this explicitly here
                st.rerun()
        else:
            col1, col2 = st.columns(2)
            # Download button for CSV
            csv_bytes = app_state.extracted_results.to_csv(index=False).encode("utf-8")
            col1.download_button(
                label="Download Extracted Results as CSV",
                data=csv_bytes,
                file_name=f"financials_{app_state.company_name}_{app_state.extract_selected_quarter}.csv",
                mime="text/csv"
            )
            col2.markdown(
                f'<a href="{app_state.extract_pdf_link}" target="_blank" download>Download Original BSE PDF ({app_state.extract_selected_quarter})</a>',
                unsafe_allow_html=True
            )

def extract_results_from_pdf_ui(user_api_key):
    with st.spinner("Extracting data...be patient, this may take a few minutes..."):
        # Filter df for selected quarter and Config == "results"
        df_filtered = app_state.bse_documents_df[
                            (app_state.bse_documents_df["Quarter_FY"] == app_state.extract_selected_quarter) & 
                            (app_state.bse_documents_df["Config"].str.lower() == "results")
                            ]
        
        if not df_filtered.empty:
            # Pick the PDF link
            app_state.extract_pdf_link = df_filtered.iloc[app_state.extract_link_count]["Link"]
            if app_state.extract_pdf_link:
                st.info(f"Letting AI do its thing on: {app_state.extract_pdf_link}")

                try:
                    df_results = extract_results_from_pdf_link(app_state.extract_selected_quarter, app_state.extract_type, app_state.extract_pdf_link, user_api_key)
                except Exception as e:
                    st.error(f"Error fetching or processing PDF: {e}")
                    st.info(traceback.format_exc())
                    df_results = None

                app_state.extracted_results = df_results
            else:
                st.warning(f'No PDF[{app_state.extract_link_count}] link found for the selected quarter.')
        else:
            st.warning("No 'results' found for this quarter.")
    

# ------------------------------
# Main APP UI
# ------------------------------
def main_app():
    st.title("Company Financial Results Profiler")
    st.write("Helps retrieve documents uploaded on BSE and extract financial results using Google Gemini model.")

    company_select_section()

    # ------------------------------
    # Step 3: Show rest only if company selected
    # ------------------------------
    if app_state.scrip_code:
        fetch_bse_documents_section()

        if app_state.bse_documents_df is not None:
            extract_results_section()

# Run the app
if __name__ == "__main__":
    main_app()
