"""QuantumFlow — Hybrid Quantum-Classical Traffic Signal Command Center (Traffic Optimization Entrypoint)."""

import os
import sys

# Ensure root directory is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Import and execute merged streamlit app
import streamlit_app
