"""QuantumFlow - Streamlit entrypoint.

Shows the quantum number-glitch loader, then the command-center dashboard.
Run with:  streamlit run streamlit_app.py
"""

import os
import sys
import streamlit as st

# Ensure package root is first in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if sys.path[0] != CURRENT_DIR:
    sys.path.insert(0, CURRENT_DIR)

st.set_page_config(
    page_title="QuantumFlow",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not st.session_state.get("loader_done", False):
    from frontend.component import webthreads_loader

    # Fullscreen black loader: hide Streamlit chrome only while it is showing
    st.markdown(
        """<style>
            .stAppHeader { display: none; }
            .block-container { padding: 0 !important; max-width: 100% !important; }
            header, footer { visibility: hidden; }
            [data-testid="stSidebar"] { display: none; }
            body, .stApp { background-color: #000000; margin: 0; overflow: hidden; }
        </style>""",
        unsafe_allow_html=True,
    )
    if webthreads_loader(key="quantumflow_number_glitch_loader") == "LOADER_COMPLETE":
        st.session_state["loader_done"] = True
        st.rerun()
else:
    from dashboard import render_dashboard

    render_dashboard()
