# libraries
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
import pandas as pd
 
# Data
r = [0,1,2,3,4]
raw_data = {'147.65.0.0/16 - 1916': [20, 1.5, 7, 10, 5], '147.65.0.0/16 - 3549': [5, 15, 5, 10, 15],'150.161.0.0/16 - 1916': [2, 15, 18, 5, 10]}
df = pd.DataFrame(raw_data)
 
# From raw value to percentage
totals = [i+j+k for i,j,k in zip(df['147.65.0.0/16 - 1916'], df['147.65.0.0/16 - 3549'], df['150.161.0.0/16 - 1916'])]
greenBars = [i / j * 100 for i,j in zip(df['147.65.0.0/16 - 1916'], totals)]
orangeBars = [i / j * 100 for i,j in zip(df['147.65.0.0/16 - 3549'], totals)]
blueBars = [i / j * 100 for i,j in zip(df['150.161.0.0/16 - 1916'], totals)]
 
# plot
barWidth = 0.85
names = ('A','B','C','D','E')
# Create green Bars
plt.bar(r, greenBars, color='#b5ffb9', edgecolor='white', width=barWidth, label="147.65.0.0/16 - 1916")
# Create orange Bars
plt.bar(r, orangeBars, bottom=greenBars, color='#f9bc86', edgecolor='white', width=barWidth, label="147.65.0.0/16 - 3549")
# Create blue Bars
plt.bar(r, blueBars, bottom=[i+j for i,j in zip(greenBars, orangeBars)], color='#a3acff', edgecolor='white', width=barWidth, label="150.161.0.0/16 - 1916")
 
# Custom x axis
plt.xticks(r, names)
plt.xlabel("group")
 
# Add a legend
plt.legend(loc='upper left', bbox_to_anchor=(1,1), ncol=1)
 
# Show graphic
plt.show()