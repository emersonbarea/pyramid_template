import os
import time

lista = list()

#print('montando a lista de listas')

#for i in range(1,50000000):
#	lista.append([i,i])

#print('lista de listas montada')
#print('\nesperando...')
#time.sleep(5)
#os.system('ps aux | sort -rnk 4 | grep teste4.py')
#time.sleep(5)

print('montando a lista de tuplas')

for i in range(1,50000000):
	lista.append((i,i))

print('lista de tuplas montada')
print('\nesperando...')
time.sleep(5)
os.system('ps aux | sort -rnk 4 | grep teste4.py')
time.sleep(5)
