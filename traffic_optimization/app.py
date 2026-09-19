import streamlit as st
from simulation.traffic_network import get_traffic_network
from simulation.kpi_calculator import calculate_kpis, get_intersection_data
from visualization.map import render_map
from visualization.charts import (
    create_density_chart,
    create_queue_chart,
    create_signal_timing_chart,
    create_performance_trend_chart,
    create_kpi_cards_html,
)
from streamlit_folium import st_folium

# Page configuration
st.set_page_config(page_title='Quantum Traffic Command Center', layout='wide')

# Custom CSS for dark futuristic UI (glass style panels, cyan/blue accents)
custom_css = '''
    <style>
    /* Global background */
    body { background-color: #0a0e18; color: #e0e5ec; }
    /* Sidebar styling */
    .css-1d391kg { background-color: #080c16; }
    /* Glass panel style */
    .glass-panel {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(8px);
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255,255,255,0.1);
    }
    /* Accent colors */
    .state-normal { color: #4edea3; }
    .state-congestion { color: #ef4444; }
    .state-emergency { color: #00f0ff; }
    </style>
''' 
st.markdown(custom_css, unsafe_allow_html=True)

# Initialize network in session state to persist simulation modifications
if 'network' not in st.session_state:
    st.session_state.network = get_traffic_network()

network = st.session_state.network
kpis = calculate_kpis(network)
intersection_data = get_intersection_data(network)

# Sidebar navigation
st.sidebar.title('🚦 Quantum Traffic Command Center')
page = st.sidebar.radio('Navigate', [
    'Live Traffic Network',
    'Traffic KPIs',
    'Quantum Optimization',
    'Emergency Green Corridor',
    'Dynamic Events',
    'Classical vs Quantum',
    'Environmental Analysis'
])

# Quick state adjuster in sidebar for testing live reactivity
with st.sidebar.expander('🛠️ Quick State Adjuster (Test Reactivity)', expanded=False):
    selected_node = st.selectbox('Select Intersection', ['I1', 'I2', 'I3', 'I4', 'I5', 'I6'], index=1)
    new_density = st.slider(
        f'{selected_node} Traffic Density', 0, 100,
        int(network.nodes[selected_node].get('traffic_density', 40))
    )
    new_queue = st.slider(
        f'{selected_node} Queue Length', 0, 30,
        int(network.nodes[selected_node].get('queue_length', 10))
    )
    if st.button('Apply State Update', use_container_width=True):
        network.nodes[selected_node]['traffic_density'] = new_density
        network.nodes[selected_node]['queue_length'] = new_queue
        st.session_state.network = network
        st.rerun()
    if st.button('Reset to Baseline', use_container_width=True):
        st.session_state.network = get_traffic_network()
        st.rerun()

# Main layout
st.title(page)

if page == 'Live Traffic Network':
    st.subheader('Live Traffic Network & Real-Time Telemetry')
    # A. Live KPI Cards
    st.markdown(create_kpi_cards_html(kpis), unsafe_allow_html=True)

    # 2-column layout: Map on left, compact telemetry charts on right
    col_map, col_analytics = st.columns([1.1, 0.9])

    with col_map:
        st.markdown("<div style='font-weight: 600; margin-bottom: 8px; color: #9ca3af;'>Spatial Traffic Map (Folium)</div>", unsafe_allow_html=True)
        folium_map = render_map(network)
        st_folium(folium_map, width=680, height=520)

    with col_analytics:
        st.markdown("<div style='font-weight: 600; margin-bottom: 8px; color: #9ca3af;'>Network Density Telemetry</div>", unsafe_allow_html=True)
        density_fig = create_density_chart(intersection_data)
        st.plotly_chart(density_fig, use_container_width=True, config={'displayModeBar': False})

        queue_fig = create_queue_chart(intersection_data)
        st.plotly_chart(queue_fig, use_container_width=True, config={'displayModeBar': False})

elif page == 'Traffic KPIs':
    st.subheader('Live Traffic Key Performance Indicators (Plotly Analytics)')
    # A. KPI Cards
    st.markdown(create_kpi_cards_html(kpis), unsafe_allow_html=True)

    # Grid of Plotly Visualizations
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        # B. Traffic Density Chart
        fig_density = create_density_chart(intersection_data)
        st.plotly_chart(fig_density, use_container_width=True)

    with row1_col2:
        # C. Queue Length Chart
        fig_queue = create_queue_chart(intersection_data)
        st.plotly_chart(fig_queue, use_container_width=True)

    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        # D. Signal Timing Chart
        fig_signals = create_signal_timing_chart(intersection_data)
        st.plotly_chart(fig_signals, use_container_width=True)

    with row2_col2:
        # E. Performance Trend Chart
        fig_trend = create_performance_trend_chart(None, kpis)
        st.plotly_chart(fig_trend, use_container_width=True)

elif page == 'Quantum Optimization':
    st.subheader('Quantum Optimization (Placeholder)')
    st.markdown("<div class='glass-panel'>[Quantum optimization results will appear here]</div>", unsafe_allow_html=True)
elif page == 'Emergency Green Corridor':
    st.subheader('Emergency Green Corridor Controls')
    st.markdown("<div class='glass-panel'>[Emergency corridor controls placeholder]</div>", unsafe_allow_html=True)
elif page == 'Dynamic Events':
    st.subheader('Trigger Dynamic Events')
    st.markdown("<div class='glass-panel'>[Buttons for Congestion, Accident, Road Closure, Emergency Vehicle]</div>", unsafe_allow_html=True)
elif page == 'Classical vs Quantum':
    st.subheader('Classical vs Quantum Comparison')
    st.markdown("<div class='glass-panel'>[Comparison charts placeholder]</div>", unsafe_allow_html=True)
elif page == 'Environmental Analysis':
    st.subheader('Environmental Impact Analysis')
    st.markdown("<div class='glass-panel'>[Environmental data placeholder]</div>", unsafe_allow_html=True)

# Footer
st.markdown("<hr style='border-color: #1b2336;'/>", unsafe_allow_html=True)
st.caption('© 2026 Quantum Traffic Command Center – Hackathon Prototype')
