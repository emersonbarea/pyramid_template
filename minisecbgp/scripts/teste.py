import pandas as pd
import time

print('\nLISTA IN')
lista1 = list(range(1,67000))
lista11 = list(range(67000,1,-1))
range1 = range(1,120000)
t1 = time.time()
for element1 in range1:
	if element1 in lista1 and element1 in lista11:
		a1 = 1
	else:
		a1 = 1
print(time.time() - t1)
# LISTA IN
# 57.619362115859985

print('\nLISTA NOT IN')
lista2 = list(range(1,67000))
lista22 = list(range(67000,1,-1))
range2 = range(1,120000)
t2 = time.time()
for element2 in range2:
	if element2 not in lista2 and element2 not in lista22:
		a2 = 1
	else:
		a2 = 1
print(time.time() - t2)
# LISTA NOT IN
# 73.21228671073914

print('\n SERIES IN .VALUES')
lista3 = list(range(1,67000))
sr3 = pd.Series(data=lista3)
lista33 = list(range(67000,1,-1))
sr33 = pd.Series(data=lista33)
range3 = range(1,120000)
t3 = time.time()
for element3 in range3:
	if element3 in sr3.values and element3 in sr33.values:
		a3 = 1
	else:
		a3 = 1
print(time.time() - t3)
# SERIES IN .VALUES
# 5.0500030517578125

print('\n SERIES NOT IN .VALUES')
lista4 = list(range(1,67000))
sr4 = pd.Series(data=lista4)
lista44 = list(range(67000,1,-1))
sr44 = pd.Series(data=lista44)
range4 = range(1,120000)
t4 = time.time()
for element4 in range4:
	if element4 not in sr4.values and element4 not in sr44.values:
		a4 = 1
	else:
		a4 = 1
print(time.time() - t4)
# SERIES NOT IN .VALUES
# 4.651928663253784

print('\nSET IN')
lista5 = list(range(1,67000))
set5 = set(lista5)
lista55 = list(range(67000,1,-1))
set55 = set(lista55)
range5 = range(1,120000)
t5 = time.time()
for element5 in range5:
	if element5 in set5 and element5 in set55:
		a5 = 1
	else:
		a5 = 1
print(time.time() - t5)
# SET IN
# 0.014009237289428711

print('\nSET NOT IN')
lista6 = list(range(1,67000))
set6 = set(lista6)
lista66 = list(range(67000,1,-1))
set66 = set(lista66)
range6 = range(1,120000)
t6 = time.time()
for element6 in range6:
	if element6 not in set6 and element6 not in set66:
		a6 = 1
	else:
		a6 = 1
print(time.time() - t6)
# SET NOT IN
# 0.013571023941040039