#graph = {11: [{22:3}, {33:3}, {55:3}],
#         22: [{11:1}, {44:3}, {55:2}],
#         33: [{11:1}, {66:3}, {77:3}],
#         44: [{22:1}, {55:1}],
#         55: [{11:1}, {22:2}, {44:3}, {66:2}],
#         66: [{33:1}, {55:2}],
#         77: [{33:1}]}

graph = {67042: [{67041: 1}], 
		 67041: [{67042: 3}, {67040: 1}], 
		 67040: [{67041: 3}, {67039: 1}, {67034: 1}], 
		 67039: [{67040: 3}, {67037: 3}, {67033: 2}], 
		 67038: [{67034: 3}, {67037: 2}], 
		 67037: [{67038: 2}, {67035: 3}, {67036: 3}, {67039: 1}], 
		 67036: [{67037: 1}, {67033: 2}], 
		 67035: [{67034: 2}, {67037: 1}, {67033: 2}], 
		 67034: [{67040: 3}, {67038: 1}, {67035: 2}], 
		 67033: [{67039: 2}, {67036: 2}, {67035: 2}]}


# finds shortest path between 2 nodes of a graph using BFS
def bfs_shortest_path(graph, start, goal):
	# keep track of all the paths to be checked
	queue = [[{start:1}]]

	all_paths = list()
	path_found = False

	# keeps looping until all possible paths have been checked
	while queue:
		print('\n queue: ', queue, type(queue))

		# pop the first path from the queue
		path = queue.pop(0)
		print('path: ', path, type(path))

		# get the last node from the path
		node = list(path[-1].keys())[0]
		print('node: ', node, type(node))

		neighbours = graph[node]
		# go through all neighbour nodes, construct a new path and
		# push it into the queue
		for neighbour in neighbours:
			print('neighbour: ', neighbour)



			# AQUI VOU VALIDAR O AGREEMENT COM O NEIGHBOUR ANTES DE COLOCAR ELE NO PATH
			parent_agreement = list(path[-1].values())[0]
			print('agreement do pai: ', parent_agreement)

			neighbour_agreement = list(neighbour.values())[0]
			print('agreement do neighbour: ', neighbour_agreement)



			if parent_agreement == 1 or (parent_agreement > 1 and neighbour_agreement == 3):
				neighbour_key = list(neighbour.keys())[0]
				new_path = path[:-1] + [list(path[-1].keys())[0]]
				new_path.append(neighbour)

				# if neighbour is not visited yet in this path
				if neighbour_key not in path:
					# append this path to all available paths if neighbour is the goal
					if neighbour_key == goal:

						path_found_length = len(new_path[:-1] + [list(new_path[-1].keys())[0]])
						for i in range(len(queue) - 1, -1, -1):
							if len(queue[i]) >= path_found_length:
								queue.pop(i)

						all_paths.append(new_path[:-1] + [list(new_path[-1].keys())[0]])
						path_found = True
					if not path_found:
						queue.append(new_path)
 
	return all_paths
 
print(bfs_shortest_path(graph, 67042, 67035))