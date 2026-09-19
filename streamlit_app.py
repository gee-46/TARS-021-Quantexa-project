"""QuantumFlow — Quantum Number Glitch Loader.

Dedicated fullscreen matrix loader component.
"""

import os
import sys
import streamlit as st

# Ensure package root is first in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if sys.path[0] != CURRENT_DIR:
    sys.path.insert(0, CURRENT_DIR)

from frontend.component import webthreads_loader

# Page configuration
st.set_page_config(
    page_title="QuantumFlow",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit header, footer, and sidebar for immersive fullscreen loader
st.markdown(
    """<style>
        .stAppHeader { display: none; }
        .block-container { padding: 0 !important; max-width: 100% !important; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        [data-testid="stSidebar"] { display: none; }
        body { background-color: #000000; margin: 0; overflow: hidden; }
        .stApp { background-color: #000000; }
    </style>""",
    unsafe_allow_html=True,
)

# Render the Number Glitch matrix loader component
webthreads_loader(key="quantumflow_number_glitch_loader")
