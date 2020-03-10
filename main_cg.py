# @Time    : 2020/3/2 22:01
# @Author  : gzzang
# @File    : main_cg
# @Project : tap_link_form

import numpy as np
import cvxpy as cp
import igraph as ig
from preparation import read_data
from preparation import set_parameter


# np.set_printoptions(formatter={'float': '{: 0.3f}'.format})

iteration_number = 5

data = read_data()
link_node_pair = data['link_node_pair']
link_capacity = data['link_capacity']
link_free = data['link_free_flow_time']
od_node_pair = data['od_node_pair']
od_demand = data['od_demand']
od_number = data['od_number']
link_number = data['link_number']
node_number = data['node_number']

parameter = set_parameter()
para_a = parameter['a']
para_b = parameter['b']

g = ig.Graph()
g.add_vertices(node_number)
g.add_edges(link_node_pair)


def cal_sp_of_one_od(link_flow, node_list):
    link_time = link_free * (1 + para_a * (link_flow / link_capacity) ** para_b)
    g.es['weight'] = link_time
    node_incidence = np.zeros_like(link_flow, dtype=bool)
    node_incidence[g.get_shortest_paths(node_list[0], to=node_list[1], weights='weight', output='epath')[0]] = True
    return node_incidence


initial_od_list_route_link_incidence = []
zero_link_flow = np.zeros_like(link_free)
for one_pair_list in od_node_pair:
    sp_link_incidence = cal_sp_of_one_od(zero_link_flow, one_pair_list)
    initial_od_list_route_link_incidence.append(sp_link_incidence.reshape([1, link_number]))

initial_route_link_incidence = np.vstack(initial_od_list_route_link_incidence)

current_link_flow = od_demand @ initial_route_link_incidence
current_od_list_route_link_incidence = initial_od_list_route_link_incidence

for i in range(iteration_number):
    for od_index, (one_route_link_incidence, one_pair_list) in enumerate(
            zip(current_od_list_route_link_incidence, od_node_pair)):
        sp_link_incidence = cal_sp_of_one_od(current_link_flow, one_pair_list)
        if not np.any(np.all(one_route_link_incidence == sp_link_incidence, axis=1)):
            current_od_list_route_link_incidence[od_index] = np.vstack((one_route_link_incidence, sp_link_incidence))

    route_link_incidence = np.vstack(current_od_list_route_link_incidence)
    od_route_number = np.array(
        [one_route_link_array.shape[0] for one_route_link_array in current_od_list_route_link_incidence])
    route_number = np.sum(od_route_number)
    od_route_incidence = np.zeros([od_number, route_number], dtype=bool)
    temp = 0
    for od_index, value in enumerate(od_route_number):
        od_route_incidence[od_index, temp:(temp + value)] = True
        temp += value

    x_route_flow = cp.Variable(route_number)
    x_link_flow = x_route_flow @ route_link_incidence
    objective = cp.Minimize(cp.sum(link_free * x_link_flow) + cp.sum(
        link_free * para_a / (para_b + 1) * link_capacity * cp.power(x_link_flow / link_capacity, para_b + 1)))
    constraints = [x_route_flow >= 0, od_route_incidence @ x_route_flow == od_demand]
    result = cp.Problem(objective=objective, constraints=constraints).solve()
    current_link_flow = x_link_flow.value

# print(route_link_incidence)
# print(od_route_incidence)
# print(x_route_flow.value)
print(current_link_flow)
print(od_route_number)
print(objective.value)

