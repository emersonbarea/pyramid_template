import multiprocessing as mp
from functools import partial
import ast
import os
import time

class Paths(object):
    def __init__(self):
        num_processes = os.cpu_count()
        self.pool = mp.Pool(processes=num_processes)
        self.manager = mp.Manager()

        file = open('topology_graph.txt',mode='r')
        contents = file.read()
        self.topology_graph = ast.literal_eval(contents)
        file.close()

        self.max_asys = 67027

    @staticmethod       
    def find_path(topology_graph, peers_list, source_set, destination_set, source):
        
        # monta a lista de destinos a procurar por um path partindo do "source"
        #   - cria um set "destination_temp" incluindo apenas os ASs de "destination_set" 
        #     que ainda não tiveram caminhos encontrados no "peers_list"

        destination_already_found = list()

        for peer in peers_list:
            if peer[0] == source:
                destination_already_found.append(peer[1])                

        destination_temp = destination_set.difference(destination_already_found)

        # procura o "path" para cada par de "source" e item de "destination_temp"
        #   - inclui um novo path para cada neighbour encontrado que teve o agreement validado
        #   - repete enquanto tiver item em "destination_temp"

        all_paths = list()
        current = mp.current_process()
        for destination in destination_temp:

            if source in [12, 14, 91, 44] or destination in [12, 14, 91, 44]:
                return

            if source == destination:
                return
            if source < destination and source in destination_temp and destination in source_set:
                return
            queue = [[{source: 1}]]
            path_found = False
            while queue:
                path = queue.pop(0)
                node = list(path[-1].keys())[0]
                neighbours = topology_graph[node]
                for neighbour in neighbours:
                    parent_agreement = list(path[-1].values())[0]
                    neighbour_agreement = list(neighbour.values())[0]
                    if parent_agreement == 1 or (parent_agreement > 1 and neighbour_agreement == 3):
                        neighbour_key = list(neighbour.keys())[0]
                        new_path = path[:-1] + [list(path[-1].keys())[0]]
                        new_path.append(neighbour)

                        if len(new_path) == 10:
                            os.system('echo "%s - %s: ABORTED" >> /tmp/all_paths_process_%s.txt' % (str(source), str(destination), str(list(current._identity)[0])))
                            return

                        if neighbour_key not in path:
                            if neighbour_key == destination:
                                path_found_length = len(new_path[:-1] + [list(new_path[-1].keys())[0]])
                                for i in range(len(queue) - 1, -1, -1):
                                    if len(queue[i]) >= path_found_length:
                                        queue.pop(i)
                                all_paths.append(new_path[:-1] + [list(new_path[-1].keys())[0]])
                                #print(str(list(current._identity)[0]), all_paths)
                                path_found = True
                            if not path_found:
                                queue.append(new_path)
            os.system('echo "%s - %s: %s" >> /tmp/all_paths_process_%s.txt' % (str(source), str(destination), str(all_paths), str(list(current._identity)[0])))
            #print('print no final da função: ', str(list(current._identity)[0]), all_paths)
            #return all_paths
        return

        # ao terminar a consulta por paths de "source" vs. "destination_temp", faça:
        #   - procurar por paths intermediários, onde:
        #       - paths maior que 3 itens ([source, item intermediário, destination]), devem ser 
        #         "quebrados" e montado os paths intermediários com as combinações possíveis
        #   - incluir esses paths na variável path que será gravada em disco
        #   - incluir os novos peers em "peers_list" para posterior utilização no loop



    def path(self):
        
        t = time.time()
        asys_list = list(range(1,self.max_asys))
        print('criando a lista de ASs: ', time.time() - t)
        
        t = time.time()
        source_set = set(asys_list)

        
        asys_list_temp1 = list(range(1, 10000))
        source_set_temp1 = set(asys_list_temp1)
        

        destination_set = set(asys_list)
        print('criando os Sets: ', time.time() - t)
        
        peers_list = self.manager.list()

        print('chamando o multiprocessing')
        function = partial(self.find_path, self.topology_graph, peers_list, source_set, destination_set)
        self.pool.map(function, source_set_temp1)
        self.pool.close()
        print('terminou o multiprocessing')

        
def main():
    print('criando o objeto')
    p = Paths()
    print('chamando a função path')
    p.path()


if __name__ == '__main__':    
    main()