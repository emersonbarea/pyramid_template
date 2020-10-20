# sample graph implemented as a dictionary
graph = {'A': [{'B':[3,1024]}, {'C':[3,1025]}, {'E':[3,1026]}],
         'B': [{'A':[1,1024]}, {'D':[3,1028]}, {'E':[2,1027]}],
         'C': [{'A':[1,1025]}, {'F':[3,1031]}, {'G':[3,1032]}],
         'D': [{'B':[1,1028]}, {'E':[1,1029]}],
         'E': [{'A':[1,1026]}, {'B':[2,1027]}, {'D':[3,1029]}, {'F':[2,1030]}],
         'F': [{'C':[1,1031]}, {'E':[2,1030]}],
         'G': [{'C':[1,1032]}]}

#graph = {'A': ['B', 'C', 'E'],
#         'B': ['A', 'D', 'E'],
#         'C': ['A', 'F', 'G'],
#         'D': ['B', 'E'],
#         'E': ['A', 'B', 'D', 'F'],
#         'F': ['C', 'E'],
#         'G': ['C']}

# finds shortest path between 2 nodes of a graph using BFS
def bfs_shortest_path(graph, start, goal):
	# keep track of all the paths to be checked
	queue = [[{start:None}]]

	# return path if start is goal
	if start == goal:
		return "That was easy! Start = goal"
 
	all_paths = list()
	path_found = False

	# keeps looping until all possible paths have been checked
	while queue:
		print('\nqueue: ', queue)

		# pop the first path from the queue
		path = queue.pop(0)
		print('path: ', path, type(path))

		# get the last node from the path
		print('path[-1]: ', path[-1], type(path[-1]))
		node = path[-1]
		
		print('node: ', node, type(node))
		
		neighbours = graph[node]
		# go through all neighbour nodes, construct a new path and
		# push it into the queue
		for neighbour in neighbours:
			print('neighbour: ', neighbour)


			# AQUI VOU VALIDAR O AGREEMENT COM O NEIGHBOUR ANTES DE COLOCAR ELE NO PATH


			new_path = list(path)
			new_path.append(neighbour)
			
			# if neighbour is not visited yet in this path
			if neighbour not in path:
				# append this path to all available paths if neighbour is the goal
				if neighbour == goal:
					print('new_path: ', new_path, type(new_path))

					all_paths.append(new_path)
					path_found = True
				if not path_found:
					queue.append(new_path)
 
	return all_paths
 
	# in case there's no path between the 2 nodes
	return "So sorry, but a connecting path doesn't exist :("
 
print('\n', bfs_shortest_path(graph, 'A', 'D'))