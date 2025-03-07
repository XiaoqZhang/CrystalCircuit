import numpy as np
import networkx as nx

class GraphGenerator:
    """
    Generate a graph from a unit cell structure.
    __________
    Parameters:
    unit_cell: pymatgen.Structure
        The unit cell structure.
    xyz_move: list
        The translation vector in Cartesian coordinates.
    direction: int
        The direction to compute electricity.
    cutoff: float
        The cutoff radius for finding neighbors.
    """
    def __init__(
            self,
            unit_cell,
            xyz_move,
            direction,
            cutoff,
    ):
        self.direction = direction
        self.cutoff = cutoff
        self.xyz_move = xyz_move

        self.original_uc = unit_cell
        self.unit_cell, self.boundary = self.update_cell()
        self.supercell, self.first_cell_index, self.middle_cell_index, self.last_cell_index = self.split_supercell()
    
        self.neighbors = self.find_neighbors()
        self.start_atoms, self.end_atoms = self.find_startend_atoms()

        self.graph = self.generate_graph()
        self.matlab_graph, self.matlab_start, self.matlab_end = self.sort_graph()

    def update_cell(self):
        cell = self.original_uc.copy()
        boundary = [np.zeros(3), np.array(self.original_uc.lattice.abc)]
        boundary[0][self.direction] += self.original_uc.lattice.abc[self.direction]
        boundary[1][self.direction] += self.original_uc.lattice.abc[self.direction]
        cell.translate_sites(range(len(cell.sites)), self.xyz_move, frac_coords=False)
        for direction in [0, 1, 2]:
            for site in cell.sites:
                if site.frac_coords[direction] >= 0.98:
                    site.frac_coords[direction] = site.frac_coords[direction] - 1
                    site.coords = cell.lattice.get_cartesian_coords(site.frac_coords)
            boundary[0][direction] += self.xyz_move[direction]
            
        return cell, boundary
    
    def split_supercell(self):
        sc = [1, 1, 1]
        sc[self.direction] = 3
        supercell = self.unit_cell * sc
        all_index = np.arange(len(supercell))
        first_cell_index = all_index[::3]
        middle_cell_index = all_index[1::3]
        last_cell_index = all_index[2::3]

        return supercell, first_cell_index, middle_cell_index, last_cell_index
    
    def find_neighbors(self):
        all_neighbors = []
        for idx in self.middle_cell_index:
            site = self.supercell[idx]
            neighbors = self.supercell.get_neighbors(site, self.cutoff)
            neighbors_index = [neighbor.index for neighbor in neighbors]
            all_neighbors.append(neighbors_index)
        return all_neighbors
    
    def find_startend_atoms(self):
        start_atoms = []
        end_atoms = []
        for i, idx in enumerate(self.middle_cell_index):
            nbr = self.neighbors[i]
            site = self.supercell[idx]
            if (any(element not in self.middle_cell_index for element in nbr)) and (site.coords[self.direction] < 0.5 * self.supercell.lattice.abc[self.direction]):
                start_atoms.append(idx)
                end_atoms.append(idx+1)
        return start_atoms, end_atoms
    
    def generate_graph(self):
        G = nx.DiGraph()
        for i, idx in enumerate(self.middle_cell_index):
            neighbors = self.neighbors[i]
            if idx in self.start_atoms:
                for nbr in neighbors:
                    if nbr in self.middle_cell_index:
                        if (not (idx, nbr) in list(G.edges)) and (not (nbr, idx) in list(G.edges)):
                            G.add_edge(idx, nbr, weight=1)
            else:
                for nbr in neighbors:
                    if (not (idx, nbr) in list(G.edges)) and (not (nbr, idx) in list(G.edges)):
                        if nbr in self.middle_cell_index:
                            site_i = self.supercell[idx]
                            site_j = self.supercell[nbr]
                            if site_i.coords[self.direction] <= site_j.coords[self.direction]:
                                G.add_edge(idx, nbr, weight=1)
                            else:
                                G.add_edge(nbr, idx, weight=1)
        
        # Connect end atoms
        for idx in self.end_atoms:
            neighbors = self.supercell.get_neighbors(self.supercell[idx], self.cutoff)
            neighbors_index = [neighbor.index for neighbor in neighbors]
            for nbr in neighbors_index:
                if (nbr in self.middle_cell_index):
                    if (not (idx, nbr) in list(G.edges)) and (not (nbr, idx) in list(G.edges)):
                        G.add_edge(nbr, idx, weight=1)

        node_pos = {node: {"pos": self.supercell[node].coords} for node in G.nodes()}
        nx.set_node_attributes(G, node_pos)
        G.remove_edges_from(nx.selfloop_edges(G))
        return G

    def sort_graph(self):
        new_index = np.arange(1, len(self.graph.nodes)+1)
        mapping = {old: new for old, new in zip(self.graph.nodes, new_index)}
        G = nx.relabel_nodes(self.graph, mapping)
        matlab_start = [mapping[x] for x in self.start_atoms]
        matlab_end = [mapping[x] for x in self.end_atoms]
        return G, matlab_start, matlab_end
            