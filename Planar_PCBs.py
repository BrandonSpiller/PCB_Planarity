import networkx as nx
import kinparse as kp
from itertools import combinations

#Netlist file input: Eclectronics MP1 Schematic, which I made on 2 layers
file = r"C:\Users\bspiller\OneDrive - Olin College of Engineering\Desktop\Eclectronics\MP1\MP1.net"

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
        # Unique components on this net (a part can have several pins on one net)
        refs = sorted({pin.ref for pin in net.pins})


        for u, v in zip(refs, refs[1:]): #chain instead of connecting all components on the same nets
            pcbGraph.add_edge(u, v)

    return pcbGraph

def findHamiltonianPath(pcbGraph):
    """
    Finds a Hamiltonian cycle in the PCB graph.

    Returns a list of vertices in cycle order.
    The starting vertex is not repeated at the end.
    Returns None if no Hamiltonian cycle is found.
    """

    nodes = list(pcbGraph.nodes())

    if len(nodes) < 3:
        return None

    # Every vertex in a Hamiltonian cycle needs at least 2 neighbors.
    for node in nodes:
        if pcbGraph.degree(node) < 2:
            return None

    start = nodes[0]
    hamiltonianPath = [start]
    visited = {start}

    def searchCycle(current):
        # If every vertex has been visited, check the closing edge.
        if len(hamiltonianPath) == len(nodes):
            if pcbGraph.has_edge(current, start):
                return hamiltonianPath.copy()
            return None

        # Try each neighbor that has not been visited yet.
        for neighbor in pcbGraph.neighbors(current):
            if neighbor not in visited:
                hamiltonianPath.append(neighbor)
                visited.add(neighbor)

                result = searchCycle(neighbor)

                if result is not None:
                    return result

                # Backtrack if this route does not form a cycle.
                visited.remove(neighbor)
                hamiltonianPath.pop()

        return None

    return searchCycle(start)


def edgesCross(edge1, edge2, position):
    """
    Checks whether two non-cycle edges (chords) cross when the vertices
    are arranged in Hamiltonian cycle order.
    """

    u, v = edge1
    x, y = edge2

    # Edges sharing an endpoint do not cross in their interiors.
    if len({u, v, x, y}) < 4:
        return False

    a, b = sorted((position[u], position[v]))
    c, d = sorted((position[x], position[y]))

    # The endpoints alternate around the Hamiltonian cycle when they *do* cross.
    return (a < c < b < d) or (c < a < d < b)

def sortSides(edges, position):
    """
    Sorts the non-cycle-edges (chords) into inside the circle, outside the circle
    and leftover for those that conflict with both
    """
    inside = []
    outside = []
    leftover = []

    for edge in edges:
        crosses_Inside = any(edgesCross(edge, other, position) for other in inside)
        crosses_Outside = any(edgesCross(edge, other, position) for other in outside)

        if not crosses_Inside:
            inside.append(edge)
        elif not crosses_Outside:
            outside.append(edge)
        else:
            leftover.append(edge)

    return inside, outside, leftover

def findPlanarity(pcbGraph):
    """
    It finds a loop through every vertex (using findHamiltonianPath)
    and links chords (non-cycle edges) whose endpoints alternate around
    it (using edgesCross). Then it checks whether those links can be
    split into inside and outside (using nx.is_bipartite, nx.bipartite.color).
    """

    #variables for if not planar
    inside = []
    outside = []
    leftover = []
    
    hamiltonianPath = findHamiltonianPath(pcbGraph)

    if hamiltonianPath is None:
        print("No Hamiltonian cycle found.")
        print("This method cannot determine whether the graph is planar.")
        return None

    # Map each vertex to its position in the cycle.
    position = {
        vertex: i
        for i, vertex in enumerate(hamiltonianPath)
    }

    print("Hamiltonian cycle:", hamiltonianPath)

    # Edges used by the Hamiltonian cycle, including the closing edge.
    n = len(hamiltonianPath)

    path_edges = {
        frozenset((
            hamiltonianPath[i],
            hamiltonianPath[(i + 1) % n]
        ))
        for i in range(n)
    }

    # All edges that are not part of the Hamiltonian cycle.
    non_path_edges = [
        (u, v) for u, v in pcbGraph.edges()
        if frozenset((u, v)) not in path_edges
    ]

    print("Non-cycle edges:", non_path_edges)

    # Each node in crossingGraph represents one non-cycle edge.
    crossingGraph = nx.Graph()
    crossingGraph.add_nodes_from(range(len(non_path_edges)))

    crossing_pairs = []

    # Compare every pair of non-cycle edges.
    for i, j in combinations(range(len(non_path_edges)), 2):
        edge1 = non_path_edges[i]
        edge2 = non_path_edges[j]

        if edgesCross(edge1, edge2, position):
            crossing_pairs.append((edge1, edge2))
            crossingGraph.add_edge(i, j)

    print("Crossing pairs:", crossing_pairs)

    # Crossing edges must be assigned to opposite sides of the cycle.
    if not nx.is_bipartite(crossingGraph):
        print("NONPLANAR: conflicting crossing constraints.")

        for i, j in crossingGraph.edges():
            # Prints out conflicting edge pairs
            print(
                f"Conflicting edges: {non_path_edges[i]} "
                f"and {non_path_edges[j]}"
            )

        #instead of return false, we're returning the inside, outside, and leftover edges
        inside, outside, leftover = sortSides(non_path_edges, position)
        return inside, outside, leftover, position


    # Assign each non-cycle edge to the inside or outside.
    colors = nx.bipartite.color(crossingGraph)

    for i, edge in enumerate(non_path_edges):
        side = "inside" if colors[i] == 0 else "outside"
        print(f"Edge {edge}: {side}")

    for i, j in crossingGraph.edges():
        print(
            f"Crossing pair: {non_path_edges[i]} and "
            f"{non_path_edges[j]} — assigned to opposite sides."
        )

    #instead of returning true, we're returning inside, outside, leftover
    #and we can use leftover being empty to signal planarity
    inside = [edge for i, edge in enumerate(non_path_edges) if colors[i] == 0]
    outside = [edge for i, edge in enumerate(non_path_edges) if colors[i] == 1]
    leftover = []
    return inside, outside, leftover, position

#assuming that the above code spits out inside, outside, and then
#also chords that conflict (leftover)
def Recursive_Layer_Count(leftoverEdges, position, layerCount=1):
    """
    Takes the leftover edges, puts them through sortSides,
    and repeats on whatever is still left over.

    Returns the total number of layers needed.
    """

    if not leftoverEdges:
        print("layer count is:", layerCount)
        return layerCount

    #Uses the same vertex positions 
    newLeftoverEdges = sortSides(leftoverEdges, position)[2] #takes only leftover edges

    return Recursive_Layer_Count(newLeftoverEdges, position, layerCount + 1)

#basically main/final function that runs everything
def countPCBLayers(pcbGraph):
    """
    Returns how many planar layers the PCB needs,
    or none if no hamiltonian cycle is found
    """
    result = findPlanarity(pcbGraph)

    # No Hamiltonian cycle, so this method can't run.
    if result is None:
        return None

    inside, outside, leftover, position = result 

    # Recursively find how many layers there are
    return Recursive_Layer_Count(leftover, position)

#Claude added this in so that it can run
if __name__ == "__main__":
    pcbGraph = netlistToGraph(file)
    print("Components:", list(pcbGraph.nodes()))
    print("Connections:", list(pcbGraph.edges()))

    layers = countPCBLayers(pcbGraph)
    print("Layers needed:", layers)