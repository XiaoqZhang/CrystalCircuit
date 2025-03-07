from pymatgen.core import Structure # For reading CIF files
import networkx as nx
from generator import GraphGenerator

# Input parameters (example: SOD_IM in x-direction)

cifname = 'SOD_IM'
cif = f"examples/{cifname}_Zn.cif" # Only keep metal atoms in the CIF file
cell = Structure.from_file(cif)

array_id = 0 # The direction of computing the electrical network
b_array, diff_array = 1, 2 # The other two directions
sys = f'{cifname}_x'
outputfile = f'examples/{sys}.m' # MATLAB script with extension .m

translation = [0, 0, 0]
cutoff = 6.5 # The length of the linker

# Initialize the graph generator

obj = GraphGenerator(cell, xyz_move=translation, direction=array_id, cutoff=cutoff)
G = obj.matlab_graph
start = obj.matlab_start
end = obj.matlab_end

# Write the MATLAB script

script = ""

script += f"% {sys} \n"

# define graph
script += f"nodes = 1:{len(G.nodes)} \n"
script += f"edges = [ \n"
for i, j in G.edges:
    script += f"{i} {j}; \n"
script += f"] \n\n"

script += f"G = digraph(edges(:, 1), edges(:,2))\n"
script += f"weights = [ \n"
for i, j in G.edges:
    script += f"{round(G.edges[i, j]['weight'], 3)}, \n"
script += f"] \n\n"
script += "G.Edges.Weight = weights\n\n"

# define start and end
script += f"startnode = {start} \n"
script += f"endnode = {end} \n\n"

# define coordinates
script += f"positions = [ \n"
for frc_pos in [pos for i, pos in nx.get_node_attributes(obj.matlab_graph, 'pos').items()]:
    script += f"[{frc_pos[0]} {frc_pos[1]} {frc_pos[2]}] \n"
script += f"] \n\n"

# creat simulink model
script += f"\n % create a simulink model \n"
script += f"sys = '{sys}' \n"
script += f"new_system(sys) \n"
script += f"open_system(sys) \n\n"

script += f"% add network blocks \n"
script += "blocknames = {} \n"
script += f"for i = 1:height(G.Edges) \n"
script += f"    node1 = G.Edges.EndNodes(i, 1) \n"
script += f"    node2 = G.Edges.EndNodes(i, 2) \n"
script += f"    resistance = G.Edges.Weight(i) \n\n"

script += f"    blockname = sprintf('R_%d_%d', node1, node2) \n"
script += "    blocknames{end+1} = blockname \n"
script += f"    add_block('fl_lib/Electrical/Electrical Elements/Resistor', [sys '/' blockname]) \n"
script += f"    set_param([sys '/' blockname], 'R', num2str(resistance)) \n"
script += f"    xpos = ((positions(node1, {array_id+1}) + positions(node2, {array_id+1})) * 1000 + positions(node1, {diff_array+1}) * 100)\n"
script += f"    ypos = ((positions(node1, {b_array+1}) + positions(node2, {b_array+1})) * 1000 + positions(node1, {diff_array+1}) * 100)\n"
script += f"    set_param([sys '/' blockname], 'Position', [xpos, ypos, xpos+200, ypos+80]) \n"
script += f"end \n\n"

script += f"% connect the blocks \n"
script += f"for i = 1:length(blocknames) \n"
script += f"    for j = i+1:length(blocknames) \n"
script += "        blockname1 = blocknames{i} \n"
script += "        blockname2 = blocknames{j} \n"
script += "        block1 = split(blockname1, '_') \n"
script += "        block2 = split(blockname2, '_') \n"
script += "        block1_x = str2num(block1{2}) \n"
script += "        block1_y = str2num(block1{3}) \n"
script += "        block2_x = str2num(block2{2}) \n"
script += "        block2_y = str2num(block2{3}) \n\n"
script += "        if block1_x == block2_x \n"
script += "            if get_param([sys '/' blockname1], 'LineHandles').LConn == -1 || get_param([sys '/' blockname2], 'LineHandles').LConn == -1 \n"
script += "                 add_line(sys, [blockname1 '/LConn 1'], [blockname2 '/LConn 1']) \n"
script += "            end \n"
script += "        end \n\n"

script += "        if block1_y == block2_y \n"
script += "            if get_param([sys '/' blockname1], 'LineHandles').RConn == -1 || get_param([sys '/' blockname2], 'LineHandles').RConn == -1 \n"
script += "                 add_line(sys, [blockname1 '/RConn 1'], [blockname2 '/RConn 1']) \n"
script += "            end \n"
script += "        end \n\n"

script += "        if block1_x == block2_y \n"
script += "            if get_param([sys '/' blockname1], 'LineHandles').LConn == -1 || get_param([sys '/' blockname2], 'LineHandles').RConn == -1 \n"
script += "                 add_line(sys, [blockname1 '/LConn 1'], [blockname2 '/RConn 1']) \n"
script += "            end \n"
script += "        end \n\n"

script += "        if block1_y == block2_x \n"
script += "            if get_param([sys '/' blockname1], 'LineHandles').RConn == -1 || get_param([sys '/' blockname2], 'LineHandles').LConn == -1 \n"
script += "                 add_line(sys, [blockname1 '/RConn 1'], [blockname2 '/LConn 1']) \n"
script += "            end \n"
script += "        end \n\n"

script += "         if ismember(block1_x, startnode) && ismember(block2_x, startnode) \n"
script += "             startpoint = blockname1 \n"
script += "             if get_param([sys '/' blockname1], 'LineHandles').LConn == -1 || get_param([sys '/' blockname2], 'LineHandles').LConn == -1 \n"
script += "                 add_line(sys, [blockname1 '/LConn 1'], [blockname2 '/LConn 1']) \n"
script += "             end \n"
script += "         end \n\n"

script += "         if ismember(block1_y, endnode) && ismember(block2_y, endnode) \n"
script += "             endpoint = blockname1 \n"
script += "             if get_param([sys '/' blockname1], 'LineHandles').RConn == -1 || get_param([sys '/' blockname2], 'LineHandles').RConn == -1 \n"
script += "                 add_line(sys, [blockname1 '/RConn 1'], [blockname2 '/RConn 1']) \n"
script += "             end \n"
script += "         end \n\n"

script += "     end \n"
script += "end \n"

script += f"% add basic blocks \n"
script += f"add_block('fl_lib/Electrical/Electrical Sources/DC Voltage Source', [sys '/V']) \n"
script += f"set_param([sys '/V'], 'v0', '1000') \n"
script += f"set_param([sys '/V'], 'Position', [0, 100, 100, 200]) \n\n"
script += f"add_block('nesl_utility/Solver Configuration', [sys '/Solver']) \n"
script += f"set_param([sys '/Solver'], 'Position', [-100, 200, 0, 250]) \n"
script += f"add_block('ee_lib/Connectors & References/Electrical Reference', [sys '/Reference']) \n"
script += f"set_param([sys '/Reference'], 'Position', [0, 300, 50, 350]) \n\n"

script += f"add_line(sys, 'V/RConn 1', 'Solver/RConn 1') \n"
script += f"add_line(sys, 'V/RConn 1', 'Reference/LConn 1') \n\n"

script += "add_block('fl_lib/Electrical/Electrical Sensors/Current Sensor', [sys '/Current Sensor']) \n"
script += "set_param([sys '/Current Sensor'], 'Position', [200, 0, 300, 100]) \n"
script += "add_block('nesl_utility/PS-Simulink Converter', [sys '/Converter']) \n"
script += "set_param([sys '/Converter'], 'Position', [350, 0, 400, 50]) \n"
script += "add_block('simulink/Sinks/Display', [sys '/Display']) \n"
script += "set_param([sys '/Display'], 'Position', [450, 0, 550, 100]) \n\n"

script += "add_line(sys, 'V/LConn 1', 'Current Sensor/LConn 1') \n"
script += "add_line(sys, 'Current Sensor/RConn 1', 'Converter/LConn 1') \n"
script += "add_line(sys, 'Converter/1', 'Display/1') \n\n"


script += "% connect the basic blocks with the network \n"
script += "add_line(sys, [startpoint '/LConn 1'], 'Current Sensor/RConn 2') \n"
script += "add_line(sys, [endpoint '/RConn 1'], 'V/RConn 1') \n\n"

script += "sim(sys) \n"
script += f"save_system(sys, '{sys}_sim') \n"

with open(f'{outputfile}', 'w') as fi:
    fi.write(script)
