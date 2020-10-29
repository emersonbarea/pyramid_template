import pandas as pd
import random
import time

print('montando a lista principal')
lista_attacker = list(range(1,5))
lista_affected = list(range(1,5))
lista_target = list(range(1,5))

lista = list()
df_lista = list()
for element_as1 in lista_attacker:
	for element_as2 in lista_affected:
		distance = random.randint(1,3)
		df_lista.append([element_as1, element_as2, distance])
		lista.append([element_as1, element_as2, distance])
df = pd.DataFrame(data=df_lista, columns = ['as1', 'as2', 'distance'])

#print(lista)
#print(df)

for attacker in lista_attacker:
	for affected in lista_affected:
		for target in lista_target:
			# pega a distãncia do affected - target ou target - affected
			affected_to_target_distance = df.loc[(df['as1'] == target) & (df['as2'] == affected)]['distance']
			print(affected_to_target_distance.tolist()[0]) 

			# pega a distância do affected - attacker ou attacker - affected

			# se affected - target >= affected - attacker, coloca o path no "válido"




#df.set_index('as1', inplace=True)
