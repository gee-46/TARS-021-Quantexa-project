"""Streamlit Custom Component for QuantumFlow WebThreads Loader."""

import os
import streamlit.components.v1 as components

# Locate the built frontend dist directory
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_BUILD_DIR = os.path.join(_CURRENT_DIR, "webthreads", "dist")

# Declare the Streamlit component pointing to the static build directory
_webthreads_component = components.declare_component(
    "webthreads_loader",
    path=_BUILD_DIR,
)


def webthreads_loader(key: str = "quantumflow_loader") -> str:
    """Render the WebThreads animated loader.

    Returns:
        str: Value emitted by the React component ('LOADER_COMPLETE' upon finishing).
    """
    return _webthreads_component(key=key, default=None)
