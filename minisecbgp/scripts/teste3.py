import multiprocessing as mp
from functools import partial
import os
import time

class Teste(object):
	def __init__(self):
		num_processes = os.cpu_count()
		self.pool = mp.Pool(processes=num_processes)
		self.manager = mp.Manager()

	@staticmethod
	def do_stuff(shared_list, zica, element):
		bla = zica
		shared_list.append([element])
	
	def teste(self):
		input_list = list(range(1,10))

		shared_list = self.manager.list()
		zica = 1

		function = partial(self.do_stuff, shared_list, zica)
		self.pool.map(function, input_list)
		self.pool.close()

		print(shared_list)


def main():
	print('criando o objeto')
	t = Teste()
	print('chamando a função')
	t.teste()

#if __name__ == '__main__':
#	main()