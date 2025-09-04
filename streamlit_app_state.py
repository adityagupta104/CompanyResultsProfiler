import streamlit as st

class StreamlitAppState:
    """
    Manages Streamlit session state in a structured way with getters and setters.
    """
    _defaults = {
            "scrip_code": None,
            "company_name": "",
            "company_matches": [],
            "bse_documents_df": None,
            "bse_documents_pivot_df": None,
            "extract_selected_quarter": None,
            "extract_type": None,
            "extract_pdf_link": None,
            "extracted_results": None,
            "extract_link_count": 0
        }
    
    def __init__(self):
        # Define default state
        keys_to_check = list(self._defaults.keys())
        for key in keys_to_check:
            if key not in st.session_state:
                st.session_state[key] = self._defaults[key]
        

    # Reset all state variables to defaults
    def reset_all(self):
        """
        Reset all state variables to their default values.
        """
        # Initialize session state with defaults if not already set
        keys_to_reset = list(self._defaults.keys())
        for key in keys_to_reset:
            st.session_state[key] = self._defaults[key]
    
    # Reset only BSE documents and extracted results related state variables
    def reset_bse_documents_and_extracted_results(self):
        """
        Reset BSE documents and extracted results related state variables.
        """
        keys_to_reset = [
            "bse_documents_df",
            "bse_documents_pivot_df",
            "extract_selected_quarter",
            "extract_type",
            "extract_pdf_link",
            "extracted_results",
            "extract_link_count",
        ]
        for key in keys_to_reset:
            st.session_state[key] = self._defaults[key]

    # Reset only extracted results related state variables
    def reset_extracted_results(self):
        """
        Reset only extracted results related state variables, not the inputs to extraction.
        """
        keys_to_reset = [
            #"extract_selected_quarter",
            #"extract_type",
            "extract_pdf_link",
            "extracted_results",
            "extract_link_count",
        ]
        for key in keys_to_reset:
            st.session_state[key] = self._defaults[key]

    # Generic getter
    def get(self, key):
        return st.session_state.get(key)

    # Generic setter
    def set(self, key, value):
        st.session_state[key] = value

    # Specific helpers for common fields
    @property
    def scrip_code(self):
        return self.get("scrip_code")

    @scrip_code.setter
    def scrip_code(self, value):
        self.set("scrip_code", value)

    @property
    def company_name(self):
        return self.get("company_name")

    @company_name.setter
    def company_name(self, value):
        self.set("company_name", value)

    @property
    def company_matches(self):
        return self.get("company_matches")

    @company_matches.setter
    def company_matches(self, value):
        self.set("company_matches", value)

    @property
    def bse_documents_df(self):
        return self.get("bse_documents_df")

    @bse_documents_df.setter
    def bse_documents_df(self, value):
        self.set("bse_documents_df", value)

    @property
    def bse_documents_pivot_df(self):
        return self.get("bse_documents_pivot_df")

    @bse_documents_pivot_df.setter
    def bse_documents_pivot_df(self, value):
        self.set("bse_documents_pivot_df", value)

    @property
    def extract_selected_quarter(self):
        return self.get("extract_selected_quarter")

    @extract_selected_quarter.setter
    def extract_selected_quarter(self, value):
        self.set("extract_selected_quarter", value)

    @property
    def extract_type(self):
        return self.get("extract_type")

    @extract_type.setter
    def extract_type(self, value):
        self.set("extract_type", value)


    @property
    def extract_pdf_link(self):
        return self.get("extract_pdf_link")

    @extract_pdf_link.setter
    def extract_pdf_link(self, value):
        self.set("extract_pdf_link", value)

    @property
    def extracted_results(self):
        return self.get("extracted_results")

    @extracted_results.setter
    def extracted_results(self, value):
        self.set("extracted_results", value)

    @property
    def extract_link_count(self):
        return self.get("extract_link_count")

    @extract_link_count.setter
    def extract_link_count(self, value):
        self.set("extract_link_count", value)
