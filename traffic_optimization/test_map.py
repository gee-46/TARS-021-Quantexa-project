"""Test for Folium spatial map generation."""

from traffic_optimization.simulation.traffic_network import get_traffic_network
from traffic_optimization.visualization.map import render_map


def test_render_map():
    """Verify traffic network graph and Folium map rendering."""
    net = get_traffic_network()
    assert len(net.nodes) == 4
    assert len(net.edges) == 3
    map_obj = render_map(net)
    assert map_obj is not None
