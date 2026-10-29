import networkx as nx
import time
import kinparse as kp


t0 = 0
t1 = 0
#Netlist file input: Eclectronics MP1 Schematic, which I made on 2 layers
#file = r"C:\Users\bspiller\Desktop\PCB_Planarity\IceBlinkPico_Schematic\iceblink.net"
file = r"C:\Users\bspiller\Desktop\PCB_Planarity\MP1_Example_Schematic\Oscillator_Example.net"

def netlistToGraph(file):
    """
    Parses a KiCad netlistfile with kinparse and builds a graph. Each
    component is a vertex. Two components get an edge if they share
    at least one net.
    """
    
    with open(file, encoding="utf-8-sig") as f:
        netlist = kp.parse_netlist(f.read())

    pcbGraph = nx.Graph()

    # Add every part, even ones not connected to anything
    for part in netlist.parts:
        pcbGraph.add_node(part.ref)

    for net in netlist.nets:
        refs = sorted({pin.ref for pin in net.pins})


        for u, v in zip(refs, refs[1:]): #chain instead of connecting all components on the same nets
            pcbGraph.add_edge(u, v)

    return pcbGraph

t0 = time.time()
nx.is_planar(netlistToGraph(file))
t1 = time.time()

print("time", t1-t0)
print(nx.is_planar(netlistToGraph(file)))
# run layer_count_algorithm()
# print_stuff 
