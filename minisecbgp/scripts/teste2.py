import multiprocessing
from multiprocessing import Manager, Pool
import time

input_list = list(range(1,10))

manager = Manager()
shared_list = manager.list()

def do_stuff(element):
    global shared_list
    shared_list.append([element])
    print(shared_list)

#def do_stuff1(element):
#    not_shared_list = list()
#    not_shared_list.append(element)
#    print(not_shared_list)

print('shared_list')

pool = Pool(processes=8)
t1 = time.time()
pool.map(do_stuff, input_list)
pool.close()
print(time.time() - t1)

print(shared_list)

#print('not_shared_list')

#pool = Pool(processes=8)
#t2 = time.time()
#pool.map(do_stuff1, input_list)
#print(time.time() - t2)