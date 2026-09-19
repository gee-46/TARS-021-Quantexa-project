import sys
import os
sys.path.append(os.getcwd())
from simulation.traffic_network import get_traffic_network
from visualization.map import render_map

net = get_traffic_network()
map_obj = render_map(net)
print('Map created, nodes:', len(net.nodes), 'edges:', len(net.edges))
