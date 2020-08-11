#! /usr/bin/env python
#! /usr/bin/env python

import gflex
import numpy as np
from matplotlib import pyplot as plt

flex = gflex.F2D()

flex.Quiet = False

flex.Method = 'FD'
flex.PlateSolutionType = 'vWC1994'
flex.Solver = 'direct'

flex.g = 9.8 # acceleration due to gravity
flex.E = 65E9 # Young's Modulus
flex.nu = 0.25 # Poisson's Ratio
flex.rho_m = 3300. # MantleDensity
flex.rho_fill = 1000. # InfiillMaterialDensity

flex.Te = 80000.
#tic thickness -- scalar but may be an array

def ReadGrid(filename):
    ascii_grid = np.loadtxt(filename, skiprows=3)
    print('shape of map:',ascii_grid.shape)
   #print(len(ascii_grid[0]),ascii_grid[0])
    tmpmax = ascii_grid.max()
    print('max value:',tmpmax)
    ascii_grid[ascii_grid == -9999] = 0
    ascii_grid = tmpmax - ascii_grid
    ascii_grid[ascii_grid == tmpmax] = 0
    ascii_grid = ascii_grid * flex.g * flex.rho_fill
    # flex.g * flex.rho_fill 
    
    return ascii_grid

#flex.qs = np.zeros((720, 360)) # Template array for surface load stresses
#flex.qs[100:150, 100:150] += 1E6 # Populating this template
flex.qs = np.zeros((800, 800))
flex.qs[200:523,50:673] = ReadGrid('test2.asc')
flex.dx = 200.
flex.dy = 200.
flex.BC_W = 'Periodic' # west boundary condition
flex.BC_E = 'Periodic' # east boundary condition
flex.BC_S = 'Periodic' # south boundary condition
flex.BC_N = 'Periodic' # north boundary condition

print(flex.qs.shape)
flex.initialize()
flex.run()
flex.finalize()

# If you want to plot the output
flex.plotChoice='both'
# An output file could also be defined here
# flex.wOutFile = 
flex.output() # Plots and/or saves output, or does nothing, depending on
              # whether flex.plotChoice and/or flex.wOutFile have been set
