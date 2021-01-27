# libraries
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
import pandas as pd
 
# Data
r = [0,1,2,3,4]
raw_data = {
'147.65.0.0/16 - undefined': [80, 79, 76, 75, 75], 
'147.65.0.0/16 - 1916': [0, 1, 4, 5, 5],
'147.65.0.0/16 - 3333': [ 0, 0, 0, 0, 0],
'147.65.0.0/16 - 3549': [0, 0, 0, 0, 0],
'147.65.0.0/16 - 6667': [0, 0, 0, 0, 0],
'150.161.0.0/16 - undefined': [3, 4, 7, 8, 9],
'150.161.0.0/16 - 1916': [74, 73, 72, 71, 70],
'150.161.0.0/16 - 3333': [3, 3, 1, 1, 1],
'208.65.153.128/25 - 0': [80, 80, 80, 80, 79],
'208.65.153.128/25 - 3549': [0, 0, 0, 0, 1]
}
df = pd.DataFrame(raw_data)
 
# From raw value to percentage
totals = [a+b+c+d+e+f+g+h+i+j for a,b,c,d,e,f,g,h,i,j in zip(
	df['147.65.0.0/16 - undefined'], 
	df['147.65.0.0/16 - 1916'],
	df['147.65.0.0/16 - 3333'],
	df['147.65.0.0/16 - 3549'],
	df['147.65.0.0/16 - 6667'],
	df['150.161.0.0/16 - undefined'],
	df['150.161.0.0/16 - 1916'],
	df['150.161.0.0/16 - 3333'],
	df['208.65.153.128/25 - 0'],
	df['208.65.153.128/25 - 3549']
	)]
aBars = [x / y * 100 for x,y in zip(df['147.65.0.0/16 - undefined'], totals)]
bBars = [x / y * 100 for x,y in zip(df['147.65.0.0/16 - 1916'], totals)]
cBars = [x / y * 100 for x,y in zip(df['147.65.0.0/16 - 3333'], totals)]
dBars = [x / y * 100 for x,y in zip(df['147.65.0.0/16 - 3549'], totals)]
eBars = [x / y * 100 for x,y in zip(df['147.65.0.0/16 - 6667'], totals)]
fBars = [x / y * 100 for x,y in zip(df['150.161.0.0/16 - undefined'], totals)]
gBars = [x / y * 100 for x,y in zip(df['150.161.0.0/16 - 1916'], totals)]
hBars = [x / y * 100 for x,y in zip(df['150.161.0.0/16 - 3333'], totals)]
iBars = [x / y * 100 for x,y in zip(df['208.65.153.128/25 - 0'], totals)]
jBars = [x / y * 100 for x,y in zip(df['208.65.153.128/25 - 3549'], totals)]

# plot
barWidth = 0.85
names = ('A','B','C','D','E')

# Create "a" Bars
plt.bar(r, aBars, 
	color='#0000FF', 
	edgecolor='white', 
	width=barWidth, 
	label="147.65.0.0/16 - undefined")

# Create "b" Bars
plt.bar(r, bBars, 
	bottom=aBars, 
	color='#FF0000', 
	edgecolor='white', 
	width=barWidth, 
	label="147.65.0.0/16 - 1916")

# Create "c" Bars
plt.bar(r, cBars, 
	bottom=[a+b for a,b in zip(aBars, bBars)], 
	color='#00FF00', 
	edgecolor='white', 
	width=barWidth, 
	label="147.65.0.0/16 - 3333")

# Create "d" Bars
plt.bar(r, dBars, 
	bottom=[a+b+c for a,b,c in zip(aBars, bBars, cBars)], 
	color='#FFFF00', 
	edgecolor='white', 
	width=barWidth, 
	label="147.65.0.0/16 - 3549")

# Create "e" Bars
plt.bar(r, eBars, 
	bottom=[a+b+c+d for a,b,c,d in zip(aBars, bBars, cBars, dBars)], 
	color='#00FFFF', 
	edgecolor='white', 
	width=barWidth, 
	label="147.65.0.0/16 - 6667")

# Create "f" Bars
plt.bar(r, fBars, 
	bottom=[a+b+c+d+e for a,b,c,d,e in zip(aBars, bBars, cBars, dBars, eBars)], 
	color='#FF00FF', 
	edgecolor='white', 
	width=barWidth, 
	label="150.161.0.0/16 - undefined")

# Create "g" Bars
plt.bar(r, gBars, 
	bottom=[a+b+c+d+e+f for a,b,c,d,e,f in zip(aBars, bBars, cBars, dBars, eBars, fBars)], 
	color='#808080', 
	edgecolor='white', 
	width=barWidth, 
	label="150.161.0.0/16 - 1916")

# Create "h" Bars
plt.bar(r, hBars, 
	bottom=[a+b+c+d+e+f+g for a,b,c,d,e,f,g in zip(aBars, bBars, cBars, dBars, eBars, fBars, gBars)], 
	color='#800000', 
	edgecolor='white', 
	width=barWidth, 
	label="150.161.0.0/16 - 3333")

# Create "i" Bars
plt.bar(r, iBars, 
	bottom=[a+b+c+d+e+f+g+h for a,b,c,d,e,f,g,h in zip(aBars, bBars, cBars, dBars, eBars, fBars, gBars, hBars)], 
	color='#800000', 
	edgecolor='white', 
	width=barWidth, 
	label="208.65.153.128/25 - 0")

# Create "j" Bars
plt.bar(r, jBars, 
	bottom=[a+b+c+d+e+f+g+h+i for a,b,c,d,e,f,g,h,i in zip(aBars, bBars, cBars, dBars, eBars, fBars, gBars, hBars, iBars)], 
	color='#808000', 
	edgecolor='white', 
	width=barWidth, 
	label="208.65.153.128/25 - 3549")


# Custom x axis
plt.xticks(r, names)
plt.xlabel("group")
 
# Add a legend
plt.legend(loc='upper left', bbox_to_anchor=(1,1), ncol=1)
 
# Show graphic
plt.show()